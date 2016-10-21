from models.alex import layers
import csv
import numpy as np
import utility
import tensorflow as tf


class FishingLocalisationLossTest(tf.test.TestCase):
    def test_simple_loss(self):
        with self.test_session():
            logits = np.array([[1, 0, 0, 1, 0], [1, 0, 1, 1, 0]], np.float32)
            targets = np.array([[1, 0, -1, 0, -1], [1, 0, 0, -1, -1]],
                               np.float32)

            loss = utility.fishing_localisation_loss(logits, targets)

            filtered_logits = logits[targets != -1]
            filtered_targets = targets[targets != -1]

            filtered_loss = tf.reduce_mean(
                tf.nn.sigmoid_cross_entropy_with_logits(filtered_logits,
                                                        filtered_targets))

            self.assertAlmostEqual(filtered_loss.eval(), loss.eval(), places=5)

    def test_loss_scaling_floor(self):
        with self.test_session():
            logits = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                               [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]], np.float32)
            targets = np.array([[0, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
                                [0, 0, -1, -1, -1, -1, -1, -1, -1, -1, -1]],
                               np.float32)

            loss = utility.fishing_localisation_loss(logits, targets)

            self.assertAlmostEqual(0.66164052, loss.eval())

    def test_loss_no_targets(self):
        with self.test_session():
            logits = np.array([[0, 0, 0, 0, 0]], np.float32)
            targets = np.array([[-1, -1, -1, -1, -1]], np.float32)

            loss = utility.fishing_localisation_loss(logits, targets)

            self.assertAlmostEqual(0.0, loss.eval())


class FishingLocalisationMseTest(tf.test.TestCase):
    def test_simple_mse(self):
        with self.test_session():
            predictions = np.array([[1, 0, 0, 1, 0], [1, 0, 1, 1, 0]],
                                   np.float32)
            targets = np.array([[1, 0, -1, 0, -1], [1, 0, 0, -1, -1]],
                               np.float32)

            mse = utility.fishing_localisation_mse(predictions, targets)

            self.assertAlmostEqual(0.33333333, mse.eval())


class InceptionLayerTest(tf.test.TestCase):
    def test_layer_shape(self):
        with self.test_session():
            input_data = [[1., 5., 6.], [2., 4., 4.], [3., 7., 9.],
                          [4., 9., 0.], [3., 7., 9.], [4., 9., 0.]]
            # Add an outer dimension to take the data from 1d to 2d
            input_data = tf.expand_dims(input_data, 0)
            # Add an outer dimension to take the data from unbatched to batch
            input_data = tf.expand_dims(input_data, 0)
            input_data_shape = tf.shape(input_data)
            self.assertAllEqual(input_data_shape.eval(), [1, 1, 6, 3])

            res = layers.misconception_layer(input_data, 3, 2, 5, True)
            res_shape = tf.shape(res)

            tf.initialize_all_variables().run()

            self.assertAllEqual(res_shape.eval(), [1, 1, 3, 5])


class PythonFixedTimeExtractTest(tf.test.TestCase):
    def test_cropped_extract(self):
        with self.test_session():
            input_data = np.array([[1., 5.], [2., 4.], [3., 7.], [4., 9.],
                                   [5., 3.], [6., 8.], [7., 2.], [8., 9.]])

            expected_result = np.array([[1., 5.], [2., 4.], [3., 7.], [4., 9.],
                                        [5., 3.], [6., 8.], [1., 5.],
                                        [2., 4.]])

            class FakeRandomState(object):
                def randint(self, min, max):
                    return 0

            res = utility.np_array_random_fixed_time_extract(
                FakeRandomState(), input_data, 5, 8, 50)

            self.assertAllEqual(res, expected_result)

    def test_uncropped_extract(self):
        with self.test_session():
            input_data = np.array([[1., 5., 6.], [2., 4., 4.], [3., 7., 9.],
                                   [4., 9., 0.]])

            res = utility.np_array_random_fixed_time_extract(
                lambda _: 0, input_data, 20, 4, 50)
            self.assertAllEqual(res, input_data)

    def test_uncropped_extract_pad(self):
        with self.test_session():
            input_data = np.array([[1., 5., 6.], [2., 4., 4.], [3., 7., 9.]])
            expected_result = np.array([[1., 5., 6.], [2., 4., 4.],
                                        [3., 7., 9.], [1., 5.,
                                                       6.], [2., 4., 4.]])

            res = utility.np_array_random_fixed_time_extract(
                lambda _: 0, input_data, 20, 5, 50)
            self.assertAllEqual(res, expected_result)


class VesselMetadataFileReader(tf.test.TestCase):
    def test_metadata_file_reader(self):
        raw_lines = [
            'mmsi,label,length\n',
            '100001,Longliner,10.0\n',
            '100002,Longliner,24.0\n',
            '100003,Longliner,7.0\n',
            '100004,Longliner,8.0\n',
            '100005,Trawler,10.0\n',
            '100006,Trawler,24.0\n',
            '100007,Passenger,24.0\n',
            '100008,Trawler,24.0\n',
            '100009,Trawler,10.0\n',
            '100010,Trawler,24.0\n',
            '100011,Tug,60.0\n',
            '100012,Tug,5.0\n',
            '100013,Tug,24.0\n',
        ]
        parsed_lines = csv.DictReader(raw_lines)
        available_vessels = set(range(100001, 100013))
        result = utility.read_vessel_multiclass_metadata_lines(
            available_vessels, parsed_lines,
            [('length', utility.vessel_categorical_length_transformer)])

        self.assertTrue('Training' in result)
        self.assertTrue('Test' in result)

        self.assertEquals(result['Test'][100001], ({'label': 'Longliner',
                                                    'length': '0-12m',
                                                    'mmsi': '100001'}, 3.0))
        self.assertEquals(result['Test'][100005], ({'label': 'Trawler',
                                                    'length': '0-12m',
                                                    'mmsi': '100005'}, 1.0))
        self.assertEquals(result['Test'][100006], ({'label': 'Trawler',
                                                    'length': '24-36m',
                                                    'mmsi': '100006'}, 1.0))
        self.assertEquals(result['Test'][100010], ({'label': 'Trawler',
                                                    'length': '24-36m',
                                                    'mmsi': '100010'}, 1.0))

        self.assertEquals(result['Training'][100002], ({'label': 'Longliner',
                                                        'length': '24-36m',
                                                        'mmsi': '100002'},
                                                       1.0))
        self.assertEquals(result['Training'][100003], ({'label': 'Longliner',
                                                        'length': '0-12m',
                                                        'mmsi': '100003'},
                                                       1.0))
        self.assertEquals(result['Training'][100004], ({'label': 'Longliner',
                                                        'length': '0-12m',
                                                        'mmsi': '100004'},
                                                       1.0))
        self.assertEquals(result['Training'][100007], ({'label': 'Passenger',
                                                        'length': '24-36m',
                                                        'mmsi': '100007'},
                                                       3.0))
        self.assertEquals(result['Training'][100008], ({'label': 'Trawler',
                                                        'length': '24-36m',
                                                        'mmsi': '100008'},
                                                       1.5))
        self.assertEquals(result['Training'][100009], ({'label': 'Trawler',
                                                        'length': '0-12m',
                                                        'mmsi': '100009'},
                                                       1.5))
        self.assertEquals(result['Training'][100011], ({'label': 'Tug',
                                                        'length': '50-75m',
                                                        'mmsi': '100011'},
                                                       1.5))
        self.assertEquals(result['Training'][100012], ({'label': 'Tug',
                                                        'length': '0-12m',
                                                        'mmsi': '100012'},
                                                       1.5))


if __name__ == '__main__':
    tf.test.main()
