import unittest

from ocs.ocs_agent import ParamError, ParamHandler, param

class TestParamHandler(unittest.TestCase):
    def test_get(self):
        params = ParamHandler({
            'int_param': 123,
            'string_param': 'blech',
            'float_param': 1e8,
            'numerical_string_param': '145.12',
            'none_param': None,
            })

        # Basic successes
        params.get('int_param', type=int)
        params.get('string_param', type=str)
        params.get('float_param', type=float)

        # Tricky successes
        params.get('int_param', type=float)
        params.get('numerical_string_param', type=float, cast=float)

        # Defaults
        self.assertEqual(params.get('missing', default=10), 10)

        # None handling
        self.assertEqual(params.get('none_param', default=None), None)
        self.assertEqual(params.get('none_param', default=123), 123)
        with self.assertRaises(ParamError):
            params.get('none_param')
        self.assertEqual(params.get('none_param', default=123,
                                    treat_none_as_missing=False), None)

        # Basic failures
        with self.assertRaises(ParamError):
            params.get('string_param', type=float)
        with self.assertRaises(ParamError):
            params.get('float_param', type=str)
        with self.assertRaises(ParamError):
            params.get('numerical_string_param', type=float)
        with self.assertRaises(ParamError):
            params.get('missing')

        # Check functions
        params.get('int_param', check=lambda i: i > 0)
        with self.assertRaises(ParamError):
            params.get('int_param', check=lambda i: i < 0)

        # Choices
        params.get('string_param', choices=['blech', 'a', 'b'])
        with self.assertRaises(ParamError):
            params.get('string_param', choices=['a', 'b'])

    def test_strays(self):
        params = ParamHandler({
            'a': 123,
            'b': 123,
            })
        params.get('a')
        params.check_for_strays(ignore=['b'])
        with self.assertRaises(ParamError):
            params.check_for_strays()
        params.get('b')
        params.check_for_strays()

    def test_decorator(self):
        # this should work
        @param('a', default=12)
        def test_func(session, params):
            pass
        # these should not
        with self.assertRaises(TypeError):
            @param('a', 12)
            def test_func(session, params):
                pass
        with self.assertRaises(TypeError):
            @param('a', invalid_keyword='something')
            def test_func(session, params):
                pass
        
    def test_decorated(self):
        @param('a', default=12)
        def func_a(session, params):
            pass

        @param('_', default=12)
        def func_nothing(session, params):
            pass

        @param('a', default=12)
        @param('_no_check_strays')
        def func_whatever(session, params):
            pass

        ParamHandler({}).batch(func_a._ocs_prescreen)
        ParamHandler({'b': 12.}).batch(func_whatever._ocs_prescreen)
        
        with self.assertRaises(ParamError):
            ParamHandler({'b': 12.}).batch(func_a._ocs_prescreen)
        with self.assertRaises(ParamError):
            ParamHandler({'b': 12.}).batch(func_nothing._ocs_prescreen)
