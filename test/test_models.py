
import pytest

from app.models import Project
from app.models import dictify


def test_dictify():
    p = Project(id=0, name='project', sample_mask='###')
    assert dictify(p) == {'id':0, 'name':'project', 'sample_mask':'###'}
