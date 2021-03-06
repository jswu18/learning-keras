from __future__ import print_function

import numpy as np
import random
import sys
import io
import keras

from collections import namedtuple
from keras.callbacks import LambdaCallback
from keras.layers import Dense, LSTM, Input
from keras.models import Model
from keras.optimizers import RMSprop
from keras.utils.data_utils import get_file

class TextGeneration:
    '''
    Using an LSTM for text generation
    This code is taken from:
        https://github.com/keras-team/keras/blob/master/examples/lstm_text_generation.py
    I am reformatting it into a class structure as way to learn and understand text generation
    I am also using the Keras Functional API instead of the Sequential API used in the example code
    '''
    def __init__(self, corpus_name='Nietzche', sentence_char_len = 40, step = 3):
        '''

        :param corpus_name: name of corpuse
        :param sentence_char_len: length of each sentence in terms of characters
        :param step: overlapping step size between training sentences
        '''
        self._model_name = corpus_name
        self._sentence_char_len = sentence_char_len

        self._text = None
        self._num_chars = None
        self._load_data(corpus_name)

        self._indices_char_dict = None
        self._char_indices_dict = None
        self._generate_char_index()

        self._sentences = None #training input
        self._next_chars = None #training target
        self._generate_training_data(step)

        self._text_generation_model = None
        self._define_model()
        return

    def _load_data(self, corpus_name):
        '''
        load corpus data

        :param corpus_name: corpus name, for now only using Nietzche data
        :return:
        '''
        CorpusEntry = namedtuple('Corpus', 'file_name website')

        #dictionary of corpuses
        dict_corpus = \
            {
            'Nietzche': CorpusEntry('nietzsche.txt', 'https://s3.amazonaws.com/text-datasets/nietzsche.txt')
            }

        #make sure corpus exists
        if dict_corpus.get(corpus_name) is None:
            raise ValueError('Invalid Corpus {}'.format(corpus_name))

        #load corpus
        path = get_file(dict_corpus[corpus_name].file_name, origin=dict_corpus[corpus_name].website)
        with io.open(path, encoding='utf-8') as f:
            text = f.read().lower()
        self._text = text
        return

    def _generate_char_index(self):
        '''
        enumerate all the characters used in text to have an index
        save characters and its corresponding index number to two dictionary
            dict 1: key->index, value->character
            dict 2: key->character, value->index
        this will be used for character embeddings
        :return:
        '''
        chars = sorted(list(set(self._text)))
        self._num_chars = len(chars)
        self._indices_char_dict = dict((i, c) for i, c in enumerate(chars))
        self._char_indices_dict = dict((c, i) for i, c in enumerate(chars))
        return

    def _generate_training_data(self, step):
        '''
        split text to create training data
        training input will be a "sentence"
            a string of characters of length sentence_char_len in vectorized form
        training output will be the next character in text after the "sentence"
            also in vectorized form

        :param step: overlapping step size between sentences
        :return:
        '''

        def vectorize_chars(char_string):
            '''
            vectorize a list of characters
            :param sentence:
            :return:
            '''
            char_vectors = np.zeros((len(char_string), self._num_chars), dtype=np.bool)
            #one hot incode
            for i, char in enumerate(char_string):
                char_vectors[i, self._char_indices_dict[char]] = 1
            return char_vectors

        text_char_len = len(self._text)
        num_sentences = int(((text_char_len - self._sentence_char_len)/step)+1)

        #initialize matricies
        sentences = np.zeros((num_sentences, self._sentence_char_len, self._num_chars), dtype=np.bool)
        next_chars = np.zeros((num_sentences, self._num_chars), dtype=np.bool)

        #load text data from corpus into matrix form
        for i in range(0, text_char_len - self._sentence_char_len, step):
            sentence_string = self._text[i: i + self._sentence_char_len]
            next_char_string = self._text[i + self._sentence_char_len]
            sentences[int(i/step)] = vectorize_chars(sentence_string)
            next_chars[int(i/step)] = vectorize_chars(next_char_string)
        self._sentences = sentences
        self._next_chars = next_chars
        return

    def _define_model(self):
        '''
        define text generation model using Functional keras

        :return:
        '''
        text_input = Input(shape=(self._sentence_char_len, self._num_chars))
        hidden_layer = LSTM(128)(text_input)
        out = Dense(self._num_chars, activation='softmax')(hidden_layer)
        self._text_generation_model = Model(text_input, out)
        optimizer = RMSprop(lr=0.01)
        self._text_generation_model.compile(loss='categorical_crossentropy', optimizer=optimizer)
        return

    def _sample(self, preds, temperature=1.0):
        # helper function to sample an index from a probability array
        preds = np.asarray(preds).astype('float64')
        preds = np.log(preds) / temperature
        exp_preds = np.exp(preds)
        preds = exp_preds / np.sum(exp_preds)
        probas = np.random.multinomial(1, preds, 1)
        return np.argmax(probas)

    def _on_epoch_end(self, epoch, _):
        # Function invoked at end of each epoch. Prints generated text.
        # This code was essentially copied over from the example code
        print()
        print('----- Generating text after Epoch: %d' % epoch)

        start_index = random.randint(0, len(self._text) - self._sentence_char_len - 1)
        sentence = self._text[start_index: start_index + self._sentence_char_len]
        self.generate_text(seed=sentence)
        if epoch%5==0:
            self.save_model(save_path='epoch_'+str(epoch)+'_')
        return

    def generate_text(self, raw_seed = None, num_char_to_generate = 400):
        '''
        Generates text using the model given a seed

        :param seed: a string that must be equal to or longer than 40 characters
        :param num_char_to_generate: the number of characters to generate after the seed
        :return: None
        '''
        if raw_seed is None:
            raw_seed = 'he who has a why to live can bear almost'
        raw_seed = raw_seed.lower()
        if len(raw_seed) > 40:
            #need to make sure seed is exactly 40 characters long
            seed = raw_seed[len(raw_seed)-40:]
        elif len(raw_seed) < 40:
            print('Please input a seed of at least 40 characters')
            return
        else:
            #seed is exactly 40 characters long
            seed = raw_seed
        for diversity in [0.2, 0.5, 1.0, 1.2]:
            sentence = seed
            print('----- diversity:', diversity)
            generated = ''
            generated += sentence
            print('----- Generating with seed: "' + raw_seed + '"')
            sys.stdout.write(raw_seed)
            for i in range(num_char_to_generate):
                x_pred = np.zeros((1, self._sentence_char_len, self._num_chars))
                for t, char in enumerate(sentence):
                    x_pred[0, t, self._char_indices_dict[char]] = 1.
                preds = self._text_generation_model.predict(x_pred, verbose=0)[0]
                next_index = self._sample(preds, diversity)
                next_char = self._indices_char_dict[next_index]

                generated += next_char
                sentence = sentence[1:] + next_char

                sys.stdout.write(next_char)
                sys.stdout.flush()
            print()
        return


    def train_model(self, print_callback_flag = True):
        '''
        train the model

        :return:
        '''
        print_callback = LambdaCallback(on_epoch_end=self._on_epoch_end)
        self._text_generation_model.fit(
                                        self._sentences,
                                        self._next_chars,
                                        batch_size=128,
                                        epochs=60,
                                        callbacks=[print_callback] if print_callback_flag else None
                                        )
        return

    def save_model(self, save_path=''):
        '''
        save the model

        :param save_path: path to save the model at
        :return:
        '''
        self._text_generation_model.save(save_path+self._model_name+'.h5')
        print('Model saved to '+save_path+self._model_name+'.h5')
        return

    def load_model(self, model_path):
        '''
        loads a model

        :param model_path: path to the model
        :return:
        '''
        self._text_generation_model = keras.models.load_model(model_path)
        return

    def prompt(self):
        '''
        Prompt for input given a message and return that value after verifying the input.

        Code base from
            https://stackoverflow.com/questions/3345202/getting-user-input

        :return:
        '''
        input_text_message = 'Please input seed: '
        input_number_of_characters = 'Please indicate the number of characters you wish to generate: '
        raw_seed = None
        num_char_to_generate = None
        while True:
            while raw_seed is None:
                raw_seed = input(input_text_message)
                if raw_seed == 'exit':
                    print('Exiting...')
                    return
                if len(raw_seed)<40:
                    print('Please input a seed of at least 40 characters')
                    raw_seed = None
            while num_char_to_generate is None:
                num_char_to_generate = input(input_number_of_characters)
                if num_char_to_generate == 'exit':
                    print('Exiting...')
                    return
                try:
                    num_char_to_generate = int(num_char_to_generate)
                except ValueError:
                    print('Please enter an integer')
                    num_char_to_generate = None
                    continue
                if num_char_to_generate < 0:
                    print('Please enter an positive integer')
                    num_char_to_generate = None
                else:
                    print('Generating text...')
                    self.generate_text(raw_seed, num_char_to_generate)
            raw_seed = None
            num_char_to_generate = None

if __name__ == '__main__':
    NietzcheTextGeneration = TextGeneration()
    NietzcheTextGeneration.train_model()
    NietzcheTextGeneration.save_model()
    NietzcheTextGeneration.load_model('Nietzche.h5')
    NietzcheTextGeneration.prompt()