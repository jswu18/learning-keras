import numpy as np
import keras
from keras.layers import Conv2D, MaxPooling2D, Input, Dense, Flatten
from keras.models import Model
from keras.utils import to_categorical
from keras.datasets import mnist
from scipy.io import loadmat

class SharedVisionModel:
    '''
    Implementing a model that will train to classify whether two MNIST digits
    are the same or different
    '''
    def __init__(self, model_name = 'sample_model'):
        self._model_name = model_name
        self.train = None
        self.test = None
        self._classification_model = None
        self._create_dataset()
        self._define_model()
        return

    def _create_dataset(self):
        '''
        Create dataset for pairs of images and whether the two digits match or not
        '''
        def get_img_pairs_and_labels(imgs, labels):
            '''
            creates image pairs with appropriate label vector
            '''
            data = {}
            num_img = imgs.shape[0]
            #reshape to dim 4
            imgs = np.reshape(imgs, (-1, 28, 28, 1))

            #get num_img random digits between 0 and num_img-1
            digit_a_idx = np.random.choice(num_img-1, num_img)
            digit_b_idx = np.random.choice(num_img-1, num_img)
            data['digit_a'] = np.take(imgs, digit_a_idx, axis=0)
            data['digit_b'] = np.take(imgs, digit_b_idx, axis=0)

            #get labels as 0 when digits don't match, 1 otherwise
            labels_a = np.take(labels, digit_a_idx, axis=0)
            labels_b = np.take(labels, digit_b_idx, axis=0)
            data['labels'] = (labels_a == labels_b).astype(int)
            return data

        #load MNIST data
        (x_train, y_train), (x_test, y_test) = mnist.load_data()

        #create pairs of images with label
        self._train = get_img_pairs_and_labels(x_train, y_train)
        self._test = get_img_pairs_and_labels(x_test, y_test)
        return

    def _define_model(self):
        '''
        define the model to be trained
        Original code taken from:
        https://keras.io/getting-started/functional-api-guide/
        '''
        # First, define the vision modules
        digit_input = Input(shape=(28, 28, 1))
        hidden_layer = Conv2D(64, (3, 3))(digit_input)
        hidden_layer = Conv2D(64, (3, 3))(hidden_layer)
        hidden_layer = MaxPooling2D((2, 2))(hidden_layer)
        out = Flatten()(hidden_layer)

        vision_model = Model(digit_input, out)

        # Then define the tell-digits-apart model
        digit_a = Input(shape=(28, 28, 1))
        digit_b = Input(shape=(28, 28, 1))

        # The vision model will be shared, weights and all
        out_a = vision_model(digit_a)
        out_b = vision_model(digit_b)

        concatenated = keras.layers.concatenate([out_a, out_b])
        out = Dense(1, activation='sigmoid')(concatenated)

        self._classification_model = Model([digit_a, digit_b], out)
        self._classification_model.compile(optimizer='rmsprop',
                                           loss='binary_crossentropy',
                                           metrics=['accuracy']
                                          )
        return

    def train_model(self):
        '''
        train the model
        '''
        self._classification_model.fit([self._train['digit_a'], self._train['digit_b']],
                                       self._train['labels'], epochs=1)
        return

    def save_model(self, save_path = ''):
        '''
        save the model
        '''
        self._classification_model.save(save_path+self._model_name+'.h5')
        print('Model saved to '+save_path+self._model_name+'.h5')
        return

    def load_model(self, model_path):
        '''
        load a model
        '''
        self._classification_model = keras.models.load_model(model_path)
        return

if __name__ == '__main__':
    mnist_digit_compare = SharedVisionModel()
    mnist_digit_compare.train_model()
    mnist_digit_compare.save_model()
