#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
#
# This file is part of Koala LMS (Learning Management system)

# Koala LMS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# We make an extensive use of the Django framework, https://www.djangoproject.com/
#
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.crypto import get_random_string

from learning.models import Resource, Activity, Course


class TestSlugFieldGenerator(TestCase):

    def setUp(self):
        get_user_model().objects.create_user(id=1, username="william-shakespeare")
        get_user_model().objects.create_user(id=2, username="emily-dickinson")
        get_user_model().objects.create_user(id=3, username="h-p-lovecraft")
        get_user_model().objects.create_user(id=4, username="arthur-conan-doyle")
        get_user_model().objects.create_user(id=5, username="leo-tolstoy")

        self.activity1 = Activity.objects.create(
            id=1,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )

        self.resource1 = Resource.objects.create(
            author=get_user_model().objects.get(pk=2),
        )

    def test_generate_slug_field_for_new_resource(self):
        r1 = Resource.objects.create(author=get_user_model().objects.get(pk=1), name="An example of a slug")
        r2 = Resource.objects.create(author=get_user_model().objects.get(pk=2), name="An example of a slug")
        r3 = Resource.objects.create(author=get_user_model().objects.get(pk=2), name="An example of a slug")
        self.assertEqual(r1.slug, "an-example-of-a-slug")
        self.assertEqual(r2.slug, "an-example-of-a-slug-1")
        self.assertEqual(r3.slug, "an-example-of-a-slug-2")
        r2.delete()
        r4 = Resource.objects.create(author=get_user_model().objects.get(pk=4), name="An example of a slug")
        self.assertEqual(r4.slug, "an-example-of-a-slug-1")

    def test_generate_slug_field_for_updated_resource(self):
        r1 = Resource.objects.create(author=get_user_model().objects.get(pk=1), name="An example of a slug")
        self.assertEqual(r1.slug, "an-example-of-a-slug")
        r1.description = "description"
        r1.save()
        self.assertEqual(r1.slug, "an-example-of-a-slug")

    def test_slug_length(self):
        self.assertEqual(50, Resource._meta.get_field('slug').max_length)
        self.assertEqual(50, Activity._meta.get_field('slug').max_length)
        self.assertEqual(50, Course._meta.get_field('slug').max_length)

    def test_long_slug_plus_one(self):
        long_name = get_random_string(length=51)
        self.assertTrue(len(long_name) > 50)

        r1 = Resource.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:50].lower(), r1.slug)

        r2 = Resource.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-1', r2.slug)

        r2 = Resource.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-2', r2.slug)

    def test_long_slug_max(self):
        long_name = get_random_string(length=50)
        self.assertEqual(50, len(long_name))

        r1 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:50].lower(), r1.slug)

        r2 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-1', r2.slug)

        r2 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-2', r2.slug)

    def test_long_slug_minus_one(self):
        long_name = get_random_string(length=49)
        self.assertEqual(49, len(long_name))

        r1 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:49].lower(), r1.slug)

        r2 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-1', r2.slug)

        r2 = Activity.objects.create(author=get_user_model().objects.get(pk=1), name=long_name)
        self.assertEqual(long_name[0:48].lower() + '-2', r2.slug)
