#!/usr/bin/env python3

import fire
import json
import os
import numpy as np
import regex as re
import tensorflow.compat.v1 as tf
import tqdm
from functools import lru_cache

tf.disable_v2_behavior()

#================================================================================
# Encoder code from encoder.py
#================================================================================

@lru_cache()
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~")+1))+list(range(ord("¡"), ord("¬")+1))+list(range(ord("®"), ord("ÿ")+1))
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8+n)
            n += 1
    cs = [chr(n) for n in cs]
    return dict(zip(bs, cs))

def get_pairs(word):
    pairs = set()
    prev_char = word[0]
    for char in word[1:]:
        pairs.add((prev_char, char))
        prev_char = char
    return pairs

class Encoder:
    def __init__(self, encoder, bpe_merges, errors='replace'):
        self.encoder = encoder
        self.decoder = {v:k for k,v in self.encoder.items()}
        self.errors = errors
        self.byte_encoder = bytes_to_unicode()
        self.byte_decoder = {v:k for k, v in self.byte_encoder.items()}
        self.bpe_ranks = dict(zip(bpe_merges, range(len(bpe_merges))))
        self.cache = {}
        self.pat = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")

    def bpe(self, token):
        if token in self.cache:
            return self.cache[token]
        word = tuple(token)
        pairs = get_pairs(word)
        if not pairs:
            return token
        while True:
            bigram = min(pairs, key = lambda pair: self.bpe_ranks.get(pair, float('inf')))
            if bigram not in self.bpe_ranks:
                break
            first, second = bigram
            new_word = []
            i = 0
            while i < len(word):
                try:
                    j = word.index(first, i)
                    new_word.extend(word[i:j])
                    i = j
                except:
                    new_word.extend(word[i:])
                    break
                if word[i] == first and i < len(word)-1 and word[i+1] == second:
                    new_word.append(first+second)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            new_word = tuple(new_word)
            word = new_word
            if len(word) == 1:
                break
            else:
                pairs = get_pairs(word)
        word = ' '.join(word)
        self.cache[token] = word
        return word

    def encode(self, text):
        bpe_tokens = []
        for token in re.findall(self.pat, text):
            token = ''.join(self.byte_encoder[b] for b in token.encode('utf-8'))
            bpe_tokens.extend(self.encoder[bpe_token] for bpe_token in self.bpe(token).split(' '))
        return bpe_tokens

    def decode(self, tokens):
        text = ''.join([self.decoder[token] for token in tokens])
        text = bytearray([self.byte_decoder[c] for c in text]).decode('utf-8', errors=self.errors)
        return text

def get_encoder(model_path):
    with open(os.path.join(model_path, 'encoder.json'), 'r') as f:
        encoder_data = json.load(f)
    with open(os.path.join(model_path, 'vocab.bpe'), 'r', encoding="utf-8") as f:
        bpe_data = f.read()
    bpe_merges = [tuple(merge_str.split()) for merge_str in bpe_data.split('\n')[1:-1]]
    return Encoder(encoder=encoder_data, bpe_merges=bpe_merges)

#================================================================================
# Model code from model.py
#================================================================================

class HParams(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def override_from_dict(self, d):
        self.__dict__.update(d)

def default_hparams():
    return HParams(
        n_vocab=0, n_ctx=1024, n_embd=768, n_head=12, n_layer=12)

def shape_list(x):
    static = x.shape.as_list()
    dynamic = tf.shape(x)
    return [dynamic[i] if s is None else s for i, s in enumerate(static)]

def softmax(x, axis=-1):
    x = x - tf.reduce_max(x, axis=axis, keepdims=True)
    ex = tf.exp(x)
    return ex / tf.reduce_sum(ex, axis=axis, keepdims=True)

def gelu(x):
    return 0.5*x*(1+tf.tanh(np.sqrt(2/np.pi)*(x+0.044715*tf.pow(x, 3))))

def norm(x, scope, *, axis=-1, epsilon=1e-5):
    with tf.variable_scope(scope):
        n_state = x.shape[-1].value
        g = tf.get_variable('g', [n_state], initializer=tf.constant_initializer(1))
        b = tf.get_variable('b', [n_state], initializer=tf.constant_initializer(0))
        u = tf.reduce_mean(x, axis=axis, keepdims=True)
        s = tf.reduce_mean(tf.square(x-u), axis=axis, keepdims=True)
        x = (x - u) * tf.rsqrt(s + epsilon)
        x = x*g + b
        return x

def split_states(x, n):
    *start, m = shape_list(x)
    return tf.reshape(x, start + [n, m//n])

def merge_states(x):
    *start, a, b = shape_list(x)
    return tf.reshape(x, start + [a*b])

def conv1d(x, scope, nf, *, w_init_stdev=0.02):
    with tf.variable_scope(scope):
        *start, nx = shape_list(x)
        w = tf.get_variable('w', [1, nx, nf], initializer=tf.random_normal_initializer(stddev=w_init_stdev))
        b = tf.get_variable('b', [nf], initializer=tf.constant_initializer(0))
        c = tf.reshape(tf.matmul(tf.reshape(x, [-1, nx]), tf.reshape(w, [-1, nf]))+b, start+[nf])
        return c

def attention_mask(nd, ns, *, dtype):
    i = tf.range(nd)[:,None]
    j = tf.range(ns)
    m = i >= j - ns + nd
    return tf.cast(m, dtype)

def attn(x, scope, n_state, *, past, hparams):
    assert x.shape.ndims == 3
    assert n_state % hparams.n_head == 0
    if past is not None:
        assert past.shape.ndims == 5
    def split_heads(x):
        return tf.transpose(split_states(x, hparams.n_head), [0, 2, 1, 3])
    def merge_heads(x):
        return merge_states(tf.transpose(x, [0, 2, 1, 3]))
    def mask_attn_weights(w):
        _, _, nd, ns = shape_list(w)
        b = attention_mask(nd, ns, dtype=w.dtype)
        b = tf.reshape(b, [1, 1, nd, ns])
        w = w*b - tf.cast(1e10, w.dtype)*(1-b)
        return w
    def multihead_attn(q, k, v):
        w = tf.matmul(q, k, transpose_b=True)
        w = w * tf.rsqrt(tf.cast(v.shape[-1].value, w.dtype))
        w = mask_attn_weights(w)
        w = softmax(w)
        a = tf.matmul(w, v)
        return a
    with tf.variable_scope(scope):
        c = conv1d(x, 'c_attn', n_state*3)
        q, k, v = map(split_heads, tf.split(c, 3, axis=2))
        present = tf.stack([k, v], axis=1)
        if past is not None:
            pk, pv = tf.unstack(past, axis=1)
            k = tf.concat([pk, k], axis=-2)
            v = tf.concat([pv, v], axis=-2)
        a = multihead_attn(q, k, v)
        a = merge_heads(a)
        a = conv1d(a, 'c_proj', n_state)
        return a, present

def mlp(x, scope, n_state, *, hparams):
    with tf.variable_scope(scope):
        nx = x.shape[-1].value
        h = gelu(conv1d(x, 'c_fc', n_state))
        h2 = conv1d(h, 'c_proj', nx)
        return h2

def block(x, scope, *, past, hparams):
    with tf.variable_scope(scope):
        nx = x.shape[-1].value
        a, present = attn(norm(x, 'ln_1'), 'attn', nx, past=past, hparams=hparams)
        x = x + a
        m = mlp(norm(x, 'ln_2'), 'mlp', nx*4, hparams=hparams)
        x = x + m
        return x, present

def past_shape(*, hparams, batch_size=None, sequence=None):
    return [batch_size, hparams.n_layer, 2, hparams.n_head, sequence, hparams.n_embd // hparams.n_head]

def expand_tile(value, size):
    value = tf.convert_to_tensor(value, name='value')
    ndims = value.shape.ndims
    return tf.tile(tf.expand_dims(value, axis=0), [size] + [1]*ndims)

def positions_for(tokens, past_length):
    batch_size = tf.shape(tokens)[0]
    nsteps = tf.shape(tokens)[1]
    return expand_tile(past_length + tf.range(nsteps), batch_size)

def model(hparams, X, past=None, scope='model', reuse=False):
    with tf.variable_scope(scope, reuse=reuse):
        results = {}
        batch, sequence = shape_list(X)
        wpe = tf.get_variable('wpe', [hparams.n_ctx, hparams.n_embd], initializer=tf.random_normal_initializer(stddev=0.01))
        wte = tf.get_variable('wte', [hparams.n_vocab, hparams.n_embd], initializer=tf.random_normal_initializer(stddev=0.02))
        past_length = 0 if past is None else tf.shape(past)[-2]
        h = tf.gather(wte, X) + tf.gather(wpe, positions_for(X, past_length))
        presents = []
        pasts = tf.unstack(past, axis=1) if past is not None else [None] * hparams.n_layer
        assert len(pasts) == hparams.n_layer
        for layer, past_layer in enumerate(pasts):
            h, present = block(h, 'h%d' % layer, past=past_layer, hparams=hparams)
            presents.append(present)
        results['present'] = tf.stack(presents, axis=1)
        h = norm(h, 'ln_f')
        h_flat = tf.reshape(h, [batch*sequence, hparams.n_embd])
        logits = tf.matmul(h_flat, wte, transpose_b=True)
        logits = tf.reshape(logits, [batch, sequence, hparams.n_vocab])
        results['logits'] = logits
        return results

#================================================================================
# Sampling code from sample.py
#================================================================================

def top_k_logits(logits, k):
    if k == 0:
        return logits
    def _top_k():
        values, _ = tf.nn.top_k(logits, k=k)
        min_values = values[:, -1, tf.newaxis]
        return tf.where(logits < min_values, tf.ones_like(logits, dtype=logits.dtype) * -1e10, logits)
    return tf.cond(tf.equal(k, 0), lambda: logits, lambda: _top_k())

def top_p_logits(logits, p):
    batch, _ = logits.shape.as_list()
    sorted_logits = tf.sort(logits, direction='DESCENDING', axis=-1)
    cumulative_probs = tf.cumsum(tf.nn.softmax(sorted_logits, axis=-1), axis=-1)
    indices = tf.stack([tf.range(0, batch), tf.maximum(tf.reduce_sum(tf.cast(cumulative_probs <= p, tf.int32), axis=-1) - 1, 0)], axis=-1)
    min_values = tf.gather_nd(sorted_logits, indices)
    return tf.where(logits < min_values, tf.ones_like(logits) * -1e10, logits)

def scheduled_top_p_logits(logits, p=0.9, step=None, total_steps=None):
    """
    Top-p sampling with adaptive temperature scheduling.
    """
    if step is None or total_steps is None:
        return top_p_logits(logits, p)

    # Temperature decreases during generation
    current_temp = tf.maximum(0.3, 1.0 - (tf.cast(step, tf.float32) / tf.cast(total_steps, tf.float32)) * 0.7)
    logits = logits / current_temp

    # Improved top-p sampling
    sorted_logits = tf.sort(logits, direction='DESCENDING', axis=-1)
    sorted_indices = tf.argsort(logits, direction='DESCENDING', axis=-1)
    cumulative_probs = tf.cumsum(tf.nn.softmax(sorted_logits, axis=-1), axis=-1)

    # Masking tokens with cumulative probability > p
    sorted_logits_masked = tf.where(
        cumulative_probs > p,
        tf.ones_like(sorted_logits) * -1e10,
        sorted_logits
    )

    # Unsort the logits back to their original order
    original_shape = shape_list(logits)
    batch_indices = tf.tile(tf.range(original_shape[0])[:, tf.newaxis], [1, original_shape[1]])
    update_indices = tf.stack([batch_indices, sorted_indices], axis=-1)
    unscrambled_logits = tf.scatter_nd(update_indices, sorted_logits_masked, original_shape)

    return unscrambled_logits

def contrastive_search(logits, hparams, context, alpha=0.6, k=5):
    """
    Selects the next token using contrastive search.
    """
    with tf.variable_scope('model', reuse=True):
        wte = tf.get_variable('wte')

    top_k_logits, top_k_indices = tf.nn.top_k(logits, k=k)

    candidate_embeddings = tf.gather(wte, top_k_indices)
    context_embeddings = tf.gather(wte, context)

    candidate_embeddings_norm = tf.nn.l2_normalize(candidate_embeddings, axis=-1)
    context_embeddings_norm = tf.nn.l2_normalize(context_embeddings, axis=-1)

    cos_sim_matrix = tf.matmul(candidate_embeddings_norm, context_embeddings_norm, transpose_b=True)

    similarity_penalty = tf.reduce_max(cos_sim_matrix, axis=-1)

    model_scores = tf.nn.softmax(top_k_logits, axis=-1)

    contrastive_scores = (1 - alpha) * model_scores - alpha * similarity_penalty

    best_candidate_indices = tf.argmax(contrastive_scores, axis=-1, output_type=tf.int32)

    batch_indices = tf.range(tf.shape(logits)[0])
    gather_indices = tf.stack([batch_indices, best_candidate_indices], axis=1)

    next_token = tf.gather_nd(top_k_indices, gather_indices)

    return tf.expand_dims(next_token, axis=1)

def sample_sequence(*, hparams, length, start_token=None, batch_size=None, context=None, temperature=1, top_k=0, top_p=1, method='classic'):
    if start_token is None:
        assert context is not None, 'Specify exactly one of start_token and context!'
    else:
        assert context is None, 'Specify exactly one of start_token and context!'
        context = tf.fill([batch_size, 1], start_token)

    def step(hparams, tokens, past=None):
        lm_output = model(hparams=hparams, X=tokens, past=past, reuse=tf.AUTO_REUSE)
        logits = lm_output['logits'][:, :, :hparams.n_vocab]
        presents = lm_output['present']
        presents.set_shape(past_shape(hparams=hparams, batch_size=batch_size))
        return {'logits': logits, 'presents': presents}

    with tf.name_scope('sample_sequence'):
        def body(past, prev, output, current_step):
            next_outputs = step(hparams, prev, past=past)
            logits = next_outputs['logits'][:, -1, :]

            if method == 'classic':
                logits = logits / tf.to_float(temperature)
                logits = top_k_logits(logits, k=top_k)
                logits = top_p_logits(logits, p=top_p)
                samples = tf.multinomial(logits, num_samples=1, output_dtype=tf.int32)
            elif method == 'contrastive':
                samples = contrastive_search(logits, hparams, output)
            elif method == 'scheduled':
                logits = scheduled_top_p_logits(logits, p=top_p, step=current_step, total_steps=length)
                samples = tf.multinomial(logits, num_samples=1, output_dtype=tf.int32)
            else:
                raise ValueError("Unknown sampling method.")

            return [
                next_outputs['presents'] if past is None else tf.concat([past, next_outputs['presents']], axis=-2),
                samples,
                tf.concat([output, samples], axis=1),
                current_step + 1,
            ]

        past, prev, output, current_step = body(None, context, context, 0)

        def cond(*args):
            return True

        _, _, tokens, _ = tf.while_loop(
            cond=cond, body=body,
            maximum_iterations=length - 1,
            loop_vars=[past, prev, output, current_step],
            shape_invariants=[
                tf.TensorShape(past_shape(hparams=hparams, batch_size=batch_size)),
                tf.TensorShape([batch_size, None]),
                tf.TensorShape([batch_size, None]),
                tf.TensorShape([]),
            ],
            back_prop=False,
        )
        return tokens

#================================================================================
# Command-line interface
#================================================================================

class GPT2:
    def generate(
        self,
        model_dir='models/124M',
        seed=None,
        nsamples=1,
        batch_size=1,
        length=None,
        temperature=0.7,
        top_k=40,
        top_p=1,
        method='classic',
        rag=False,
        prompt="",
    ):
        """
        Generates text samples from a model.
        """
        model_path = os.path.expanduser(os.path.expandvars(model_dir))
        enc = get_encoder(model_path)
        hparams = default_hparams()
        with open(os.path.join(model_path, 'hparams.json')) as f:
            hparams.override_from_dict(json.load(f))

        if length is None:
            length = hparams.n_ctx // 2
        elif length > hparams.n_ctx:
            raise ValueError("Can't get samples longer than window size: %s" % hparams.n_ctx)

        with tf.Session(graph=tf.Graph()) as sess:
            np.random.seed(seed)
            tf.set_random_seed(seed)

            context = tf.placeholder(tf.int32, [batch_size, None])

            if not prompt and not rag:
                # Unconditional generation
                context_tokens = [enc.encoder['<|endoftext|>']]
            else:
                if rag and prompt:
                    knowledge = self._retrieve_knowledge(prompt)
                    augmented_prompt = f"Contexte: {knowledge}\n\nQuestion: {prompt}\n\nRéponse:"
                    context_tokens = enc.encode(augmented_prompt)
                else:
                    context_tokens = enc.encode(prompt)

            output = sample_sequence(
                hparams=hparams, length=length,
                context=context,
                batch_size=batch_size,
                temperature=temperature, top_k=top_k, top_p=top_p,
                method=method
            )

            saver = tf.train.Saver()
            ckpt = tf.train.latest_checkpoint(model_path)
            saver.restore(sess, ckpt)

            generated = 0
            while nsamples == 0 or generated < nsamples:
                out = sess.run(output, feed_dict={
                    context: [context_tokens for _ in range(batch_size)]
                })
                for i in range(batch_size):
                    generated += batch_size
                    text = enc.decode(out[i])
                    print("=" * 40 + " SAMPLE " + str(generated) + " " + "=" * 40)
                    print(text)

    def _retrieve_knowledge(self, prompt, knowledge_base_dir='knowledge_base'):
        """
        A keyword-based retriever that ignores common stop words.
        """
        stop_words = set([
            "a", "à", "après", "au", "aux", "avec", "ce", "ceci", "cela", "ces", "c'est",
            "dans", "de", "des", "du", "elle", "en", "et", "eux", "il", "ils", "je",
            "la", "le", "les", "leur", "lui", "ma", "mais", "me", "même", "mes", "moi",
            "mon", "ne", "nos", "notre", "nous", "on", "ou", "par", "pas", "pour", "qu'",
            "que", "quel", "quelle", "quelles", "quels", "qui", "sa", "sans", "se", "ses",
            "son", "sur", "ta", "te", "tes", "toi", "ton", "tu", "un", "une", "vos",
            "votre", "vous", "y", "est"
        ])

        # Helper function to clean and tokenize text
        def clean_text(text):
            # Remove punctuation and convert to lowercase
            text = re.sub(r'[^\w\s]', '', text.lower())
            return set(text.split()) - stop_words

        prompt_keywords = clean_text(prompt)
        best_doc = ""
        max_score = 0

        if not os.path.exists(knowledge_base_dir):
            return ""

        for filename in os.listdir(knowledge_base_dir):
            if filename.endswith(".txt"):
                with open(os.path.join(knowledge_base_dir, filename), 'r', encoding='utf-8') as f:
                    content = f.read()
                    content_keywords = clean_text(content)
                    score = len(prompt_keywords.intersection(content_keywords))
                    if score > max_score:
                        max_score = score
                        best_doc = content

        # If no document has a score > 0, return a neutral message
        if max_score == 0:
            return "Aucune information pertinente n'a été trouvée dans la base de connaissance."

        return best_doc

    def finetune(
        self,
        dataset_path,
        model_name='124M',
        batch_size=1,
        learning_rate=1e-4,
        epochs=1,
        output_dir=None,
    ):
        """
        Fine-tunes the model on a dataset.
        """
        if output_dir is None:
            output_dir = f'models/{model_name}-finetuned'

        model_path = os.path.join('models', model_name)

        enc = get_encoder(model_path)
        hparams = default_hparams()
        with open(os.path.join(model_path, 'hparams.json')) as f:
            hparams.override_from_dict(json.load(f))

        dataset = self._load_dataset(enc, dataset_path)

        with tf.Session(graph=tf.Graph()) as sess:
            context = tf.placeholder(tf.int32, [batch_size, None])

            output = model(hparams=hparams, X=context)
            logits = output['logits']

            labels = context[:, 1:]
            logits = logits[:, :-1]

            loss = tf.losses.sparse_softmax_cross_entropy(labels=labels, logits=logits)

            model_vars = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope='model')
            train_op = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(loss)

            restore_saver = tf.train.Saver(var_list=model_vars)
            save_saver = tf.train.Saver()

            sess.run(tf.global_variables_initializer())

            ckpt = tf.train.latest_checkpoint(model_path)
            print(f"Loading checkpoint {ckpt}")
            restore_saver.restore(sess, ckpt)

            print(f"Starting fine-tuning for {epochs} epochs...")
            for epoch in range(epochs):
                print(f"--- Epoch {epoch+1}/{epochs} ---")
                total_loss = 0

                for i in tqdm.tqdm(range(0, len(dataset), batch_size)):
                    batch = dataset[i:i+batch_size]
                    if not batch: continue

                    data = batch[0]
                    tokens = data['prompt'] + data['completion']
                    tokens = tokens[:hparams.n_ctx]

                    batch_tokens = np.array(tokens).reshape(batch_size, -1)

                    _, current_loss = sess.run([train_op, loss], feed_dict={context: batch_tokens})
                    total_loss += current_loss

                print(f"Epoch {epoch+1} average loss: {total_loss / len(dataset)}")

            print("Fine-tuning complete. Saving model...")
            os.makedirs(output_dir, exist_ok=True)
            save_saver.save(sess, os.path.join(output_dir, "model.ckpt"))

            for filename in ["encoder.json", "hparams.json", "vocab.bpe"]:
                from shutil import copyfile
                copyfile(os.path.join(model_path, filename), os.path.join(output_dir, filename))

            print(f"Model saved to {output_dir}")

    def _load_dataset(self, enc, path):
        """
        Loads a .jsonl dataset, tokenizes it, and returns a list of dictionaries.
        """
        dataset = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                prompt_tokens = enc.encode(data['prompt'])
                completion_tokens = enc.encode(data['completion'])
                dataset.append({
                    'prompt': prompt_tokens,
                    'completion': completion_tokens
                })
        return dataset

if __name__ == '__main__':
    fire.Fire(GPT2)
