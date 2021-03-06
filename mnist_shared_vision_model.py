import numpy as np
import keras
from keras.layers import Conv2D, MaxPooling2D, Input, Dense, Flatten, Dropout
from keras.models import Model
from keras.datasets import mnist

class SharedVisionModel:
    '''
    Implementing a model that will train to classify whether two MNIST digits
    are the same or different
    '''
    def __init__(self, model_name='sample_model', epochs=4, batch_size=32, train_size=60000, test_size=18000):
        self._model_name = model_name
        self._epochs = epochs
        self._batch_size = batch_size
        self._train_size = train_size
        self._test_size = test_size
        self._train = None
        self._test = None
        self._classification_model = None
        self._create_data_set()
        self._define_model()
        return

    def _create_data_set(self):
        '''
        Create data set for pairs of images and whether the two digits match or not
        '''
        def get_img_pairs_and_labels(imgs, labels, desired_size):
            '''
            creates image pairs with appropriate label vector
            '''
            half_desired_size = int(desired_size/2)
            data = {}
            num_img = imgs.shape[0]
            #reshape to dim 4
            imgs = np.reshape(imgs, (-1, 28, 28, 1))

            #get num_img random digits between 0 and num_img-1
            digit_a_idx = np.random.choice(num_img-1, desired_size*10)
            digit_b_idx = np.random.choice(num_img-1, desired_size*10)
            digit_a = np.take(imgs, digit_a_idx, axis=0)
            digit_b = np.take(imgs, digit_b_idx, axis=0)

            #get labels as 0 when digits don't match, 1 otherwise
            labels_a = np.take(labels, digit_a_idx, axis=0)
            labels_b = np.take(labels, digit_b_idx, axis=0)
            labels = (labels_a == labels_b).astype(int)

            #need to make data even in terms of digits that match vs don't match
            idx_false = np.nonzero(labels)[0]
            mask_true = np.ones(len(labels))
            mask_true[idx_false] = 0
            idx_true = np.nonzero(mask_true)[0]
            idx_false = idx_false[0:half_desired_size]
            idx_true = idx_true[0:half_desired_size]
            idx_images = np.concatenate((idx_true, idx_false))
            data['labels'] = labels[idx_images]
            data['digit_a'] = digit_a[idx_images]
            data['digit_b'] = digit_b[idx_images]

            #make labels that will be used as the secondary output by the vision model
            data['digit_a_labels'] = np.zeros((half_desired_size*2, 10))
            data['digit_b_labels'] = np.zeros((half_desired_size*2, 10))
            data['digit_a_labels'][np.arange(half_desired_size*2), labels_a[idx_images]] = 1
            data['digit_b_labels'][np.arange(half_desired_size*2), labels_b[idx_images]] = 1
            return data

        #load MNIST data
        (x_train, y_train), (x_test, y_test) = mnist.load_data()

        #create pairs of images with label
        self._train = get_img_pairs_and_labels(x_train, y_train, desired_size=self._train_size)
        self._test = get_img_pairs_and_labels(x_test, y_test, desired_size=self._test_size)
        return

    def _define_model(self):
        '''
        define the model to be trained
        Original code taken from:
        https://keras.io/getting-started/functional-api-guide/
        '''
        # First, define the vision modules
        digit_input = Input(shape=(28, 28, 1))
        hidden_layer = Conv2D(32, (3, 3), activation='relu')(digit_input)
        hidden_layer = Conv2D(64, (3, 3), activation='relu')(hidden_layer)
        hidden_layer = MaxPooling2D((2, 2))(hidden_layer)
        hidden_layer = Dropout(0.25)(hidden_layer)
        hidden_layer = Flatten()(hidden_layer)
        hidden_layer = Dense(128, activation='relu')(hidden_layer)
        hidden_layer = Dropout(0.25)(hidden_layer)
        out = Dense(10, activation='softmax')(hidden_layer)

        vision_model = Model(digit_input, out)

        # Then define the tell-digits-apart model
        digit_a = Input(shape=(28, 28, 1))
        digit_b = Input(shape=(28, 28, 1))

        # The vision model will be shared, weights and all
        out_a = vision_model(digit_a)
        out_b = vision_model(digit_b)

        out = keras.layers.Dot(axes=1)([out_a, out_b])

        self._classification_model = Model(inputs=[digit_a, digit_b], outputs=[out, out_a, out_b])
        self._classification_model.compile( optimizer=keras.optimizers.Adadelta(),
                                            loss='binary_crossentropy',
                                            metrics=['accuracy'],
                                            loss_weights = [0.1, 1, 1]
                                          )
        return

    def test_single_train_input(self):
        '''
        debugging tool, prints out the layer outputs to make sure they are correct

        :return: None
        '''
        print('#############################')
        print('Reference')
        print('Digit A Labels: {}'.format(self._test['digit_a_labels']))
        print('Digit B Labels: {}'.format(self._test['digit_b_labels']))
        print('Classification Label: {}'.format(self._test['labels']))
        output = self._classification_model.predict([self._test['digit_a'], self._test['digit_b']])
        print('#############################')
        print('Predictions')
        print('Digit A Labels: {}'.format(output[1]))
        print('Digit B Labels: {}'.format(output[2]))
        print('Classification Label: {}'.format(output[0]))
        print('#############################')
        return


    def train_model(self):
        '''
        train the model
        '''
        self._classification_model.fit([self._train['digit_a'], self._train['digit_b']],
                                       [self._train['labels'], self._train['digit_a_labels'], self._train['digit_b_labels']],
                                       epochs=self._epochs,
                                       batch_size=self._batch_size,
                                       validation_data=([self._test['digit_a'], self._test['digit_b']],
                                                        [self._test['labels'], self._test['digit_a_labels'], self._test['digit_b_labels']]),
                                       )
        return

    def save_model(self, save_path=''):
        '''
        save the model
        '''
        self._classification_model.save(save_path+self._model_name+'.h5')
        print('Model saved to '+save_path+self._model_name+'.h5')
        return

    def evaluate_model(self):
        '''
        Evaluate model using test set data
        :return:
        '''

        score = self._classification_model.evaluate([self._test['digit_a'], self._test['digit_b']],
                                                    [self._test['labels'], self._test['digit_a_labels'], self._test['digit_b_labels']])
        print('Test loss: {}'.format(score[0]))
        print('Test accuracy: {}'.format(score[1]))
        return

    def load_model(self, model_path):
        '''
        load a model
        '''
        self._classification_model = keras.models.load_model(model_path)
        return

if __name__ == '__main__':
    MNISTDigitCompare = SharedVisionModel()
    MNISTDigitCompare.train_model()
    MNISTDigitCompare.evaluate_model()
    MNISTDigitCompare.save_model()
