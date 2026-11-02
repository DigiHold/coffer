import pytest

# The helpers assert too, so pytest rewrites them for readable failures.
pytest.register_assert_rewrite("tests.shop")
