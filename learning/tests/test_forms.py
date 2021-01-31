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
# noinspection PyProtectedMember
from taggit.managers import _TaggableManager

from learning.forms import CourseFormMixin
from learning.models import CourseState, CourseAccess


class CourseForms(TestCase):

    def setUp(self):
        pass

    def test_course_form_mixin_clean(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.PUBLISHED.name,
            "access": CourseAccess.PUBLIC.name,
            "registration_enabled": True,
        }

        non_testable_data = dict(data)
        non_testable_data.update({
            "tags": "tag_one, tag_two",
            "author": user.id
        })

        form = CourseFormMixin(
            non_testable_data
        )

        self.assertTrue(form.is_valid())
        course = form.save()
        for key, value in data.items():
            self.assertEqual(getattr(course, key), value)
        self.assertEqual(course.author, user)
        self.assertIsInstance(course.tags, _TaggableManager)

    def test_course_form_mixin_clean_registration_enabled_draft(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.DRAFT.name,
            "access": CourseAccess.PUBLIC.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertFalse(form.is_valid())

        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.DRAFT.name,
            "access": CourseAccess.PUBLIC.name,
            "registration_enabled": False,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertTrue(form.is_valid())

    def test_course_form_mixin_clean_registration_enabled_archived(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.ARCHIVED.name,
            "access": CourseAccess.PUBLIC.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertFalse(form.is_valid())

        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.ARCHIVED.name,
            "access": CourseAccess.PUBLIC.name,
            "registration_enabled": False,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertTrue(form.is_valid())

    def test_course_restricted_access_course_published(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.PUBLISHED.name,
            "access": CourseAccess.COLLABORATORS_ONLY.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertFalse(form.is_valid())

        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.PUBLISHED.name,
            "access": CourseAccess.PRIVATE.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertFalse(form.is_valid())

        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.PUBLISHED.name,
            "access": CourseAccess.STUDENTS_ONLY.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(
            data
        )
        self.assertTrue(form.is_valid())


class TestCustomClassOnFormMixin(TestCase):

    def test_no_class_on_global_errors(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "name": "A course name",
            "description": "A course description",
            "state": CourseState.PUBLISHED.name,
            "access": CourseAccess.PRIVATE.name,
            "registration_enabled": True,
            "tags": "tag_one, tag_two",
            "author": user.id
        }
        form = CourseFormMixin(data)
        self.assertFalse(form.is_valid())
        for field in form.fields.values():
            field_class = field.widget.attrs.get('class', str())
            self.assertNotIn("is-valid", field_class)
            self.assertNotIn("is-invalid", field_class)

    def test_valid_and_invalid_class_on_form_fields(self):
        user = get_user_model().objects.create_user(id=1, username="william-shakespeare")
        data = {
            "description": "A description",
            "author": user.id
        }
        form = CourseFormMixin(data)
        self.assertFalse(form.is_valid())
        # Check if error fields have the “is-invalid” class attribute
        for key in form.errors.as_data():
            form_class = form.fields[key].widget.attrs.get('class', str())
            self.assertIn("is-invalid", form_class)

        # Check if non-error fields have the “is-valid” class attribute
        for key in ("author", "description"):
            self.assertIn("is-valid", form.fields[key].widget.attrs.get('class', str()))
