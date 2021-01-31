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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase

from learning.exc import ActivityNotReusableError, ActivityNotReusableOnlyAuthorError, ResourceAlreadyOnActivityError, \
    ResourceNotReusableError, \
    ResourceIsNotLinkedWithThisActivityError
from learning.models import Activity, ActivityAccess, Course, CourseAccess, CourseState, CourseActivity, ActivityReuse, \
    Resource, ResourceReuse, CollaboratorRole, ActivityCollaborator


class ActivityTestCase(TestCase):

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
        self.activity2 = Activity.objects.create(
            id=2,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        self.activity3 = Activity.objects.create(
            id=3,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        self.activity4 = Activity.objects.create(
            id=4,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )

        self.public_course = Course.objects.create(
            id=2,
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PUBLIC.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True
        )


class ActivityUserPermsTest(ActivityTestCase):

    def test_perms_for_connected_user_on_public_activity(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.assertNotEqual(unknown_user, self.activity1.author)
        self.assertNotIn(unknown_user, self.activity1.object_collaborators.all())
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertEqual(sorted(['view_activity']), sorted(self.activity1.get_user_perms(unknown_user)))

    def test_perms_for_anonymous_user_on_public_activity(self):
        anonymous_user = AnonymousUser()
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertEqual(sorted(['view_activity']), sorted(self.activity1.get_user_perms(anonymous_user)))

    def test_perms_for_author_on_public_activity(self):
        user = self.activity1.author
        self.activity1.access = ActivityAccess.PUBLIC.name
        expected_perms = [
            "view_activity", "delete_activity", "add_activity", "change_activity",
            "view_similar_activity", "view_usage_activity", "toggle_important_question_activity",
            "add_collaborator_activity", "view_collaborators_activity", "change_collaborator_activity",
            "delete_collaborator_activity", 'add_objective_activity', 'change_objective_activity',
            'delete_objective_activity',
            'view_objective_activity',

        ]
        self.assertEqual(sorted(expected_perms), sorted(self.activity1.get_user_perms(user)))

    def test_perms_for_author_on_private_activity(self):
        user = self.activity1.author
        self.activity1.access = ActivityAccess.PRIVATE.name
        expected_perms = [
            "view_activity", "delete_activity", "add_activity", "change_activity",
            "view_similar_activity", "view_usage_activity", "toggle_important_question_activity",
            "add_collaborator_activity", "view_collaborators_activity", "change_collaborator_activity",
            "delete_collaborator_activity", 'add_objective_activity', 'change_objective_activity',
            'delete_objective_activity',
            'view_objective_activity',
        ]
        self.assertEqual(sorted(expected_perms), sorted(self.activity1.get_user_perms(user)))

    def test_perms_for_author_on_existing_course_activity(self):
        user = self.activity1.author
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        expected_perms = [
            "view_activity", "delete_activity", "add_activity", "change_activity",
            "view_similar_activity", "view_usage_activity", "toggle_important_question_activity",
            "add_collaborator_activity", "view_collaborators_activity", "change_collaborator_activity",
            "delete_collaborator_activity", 'add_objective_activity', 'change_objective_activity',
            'delete_objective_activity',
            'view_objective_activity',

        ]
        self.assertEqual(sorted(expected_perms), sorted(self.activity1.get_user_perms(user)))

    def test_perms_for_connected_on_activity_linked_to_public_course(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PUBLIC.name
        self.assertIn("view_course", self.public_course.get_user_perms(unknown_user))
        self.public_course.save()

        # Link the activity with the course
        CourseActivity.objects.create(course=self.public_course, activity=self.activity1, rank=1)

        self.assertIn("view_activity", self.activity1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_activity_linked_to_public_course(self):
        anonymous_user = AnonymousUser()
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PUBLIC.name
        self.assertIn("view_course", self.public_course.get_user_perms(anonymous_user))
        self.public_course.save()

        # Link the activity with the course
        CourseActivity.objects.create(course=self.public_course, activity=self.activity1, rank=1)

        self.assertIn("view_activity", self.activity1.get_user_perms(anonymous_user))

    def test_perms_for_connected_on_activity_linked_to_private_course(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PRIVATE.name
        self.assertNotIn("view_course", self.public_course.get_user_perms(unknown_user))
        self.public_course.save()

        # Link the activity with the course
        CourseActivity.objects.create(course=self.public_course, activity=self.activity1, rank=1)

        self.assertNotIn("view_activity", self.activity1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_activity_linked_to_private_course(self):
        anonymous_user = AnonymousUser()
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PRIVATE.name
        self.assertNotIn("view_course", self.public_course.get_user_perms(anonymous_user))
        self.public_course.save()

        # Link the activity with the course
        CourseActivity.objects.create(course=self.public_course, activity=self.activity1, rank=1)

        self.assertNotIn("view_activity", self.activity1.get_user_perms(anonymous_user))

    def test_perms_for_connected_on_activity_not_linked_to_public_course(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PUBLIC.name
        self.assertIn("view_course", self.public_course.get_user_perms(unknown_user))
        self.public_course.save()

        self.assertNotIn("view_activity", self.activity1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_activity_not_linked_to_public_course(self):
        anonymous_user = AnonymousUser()
        self.activity1.access = ActivityAccess.EXISTING_COURSES.name
        self.assertNotIn("view_activity", self.public_course.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.public_course.access = CourseAccess.PUBLIC.name
        self.assertIn("view_course", self.public_course.get_user_perms(anonymous_user))
        self.public_course.save()

        self.assertNotIn("view_activity", self.activity1.get_user_perms(anonymous_user))


class ActivityTest(ActivityTestCase):
    """
    Default values
    """

    def test_default_values_for_attributes(self):
        activity = Activity.objects.create(author=get_user_model().objects.get(pk=1),
                                           name="A sample name to test the @slug generator")
        self.assertEqual(activity.access, ActivityAccess.PUBLIC.name)
        self.assertEqual(activity.reuse, ActivityReuse.ONLY_AUTHOR.name)
        self.assertEqual(activity.slug, "a-sample-name-to-test-the-slug-generator")

    """
    Property object_collaborators
    """

    def test_object_collaborators(self):
        ActivityCollaborator.objects.create(
            collaborator=get_user_model().objects.get(pk=1), role=CollaboratorRole.TEACHER.name,
            activity=self.activity1
        )
        self.assertEqual(1, self.activity1.object_collaborators.count())
        self.assertEqual(get_user_model().objects.get(pk=1), self.activity1.object_collaborators.first().collaborator)
        self.assertEqual(CollaboratorRole.TEACHER.name, self.activity1.object_collaborators.first().role)
        self.assertEqual(self.activity1, self.activity1.object_collaborators.first().activity)

    """
    Method add_resource
    """

    def test_add_resource_is_already_linked_error(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=2),
                                           reuse=ResourceReuse.NO_RESTRICTION.name)
        self.activity1.resources.add(resource)
        self.assertIn(resource, self.activity1.resources.all())
        self.assertEqual(1, self.activity1.resources.count())
        with self.assertRaises(ResourceAlreadyOnActivityError):
            self.activity1.add_resource(resource)
        self.assertIn(resource, self.activity1.resources.all())
        self.assertEqual(1, self.activity1.resources.count())

    def test_add_resource_is_not_reusable(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=2),
                                           reuse=ResourceReuse.NON_REUSABLE.name)
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())
        with self.assertRaises(ResourceNotReusableError):
            self.assertFalse(self.activity1.add_resource(resource))
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())

    def test_add_resource_is_reusable(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=2),
                                           reuse=ResourceReuse.NO_RESTRICTION.name)
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())
        self.activity1.add_resource(resource)
        self.assertIn(resource, self.activity1.resources.all())
        self.assertEqual(1, self.activity1.resources.count())

    """
    Method remove_resource
    """

    def test_remove_resource_not_already_linked_error(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=2))
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())
        with self.assertRaises(ResourceIsNotLinkedWithThisActivityError):
            self.activity1.remove_resource(resource)
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())

    def test_remove_resource(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=2))
        self.activity1.resources.add(resource)
        self.assertIn(resource, self.activity1.resources.all())
        self.assertEqual(1, self.activity1.resources.count())
        self.activity1.remove_resource(resource)
        self.assertNotIn(resource, self.activity1.resources.all())
        self.assertEqual(0, self.activity1.resources.count())

    """
    Method is_reusable
    """

    def test_is_reusable_activity_not_reusable_error(self):
        self.activity1.reuse = ActivityReuse.NON_REUSABLE.name
        with self.assertRaises(ActivityNotReusableError):
            self.activity1.is_reusable()

    def test_is_reusable_activity_only_author_error(self):
        unknown_user = get_user_model().objects.create_user(username="unknown_user")
        self.activity1.reuse = ActivityReuse.ONLY_AUTHOR.name
        self.public_course.author = unknown_user
        with self.assertRaises(ActivityNotReusableOnlyAuthorError):
            self.activity1.is_reusable(for_course=self.public_course)

    def test_is_reusable_activity_only_author_missing_parameter(self):
        self.activity1.reuse = ActivityReuse.ONLY_AUTHOR.name
        with self.assertRaises(RuntimeError):
            self.activity1.is_reusable()

    def test_is_reusable_activity_no_restriction(self):
        self.activity1.reuse = ActivityReuse.NO_RESTRICTION.name
        self.assertTrue(self.activity1.is_reusable())

    """
    Method clean
    """

    def test_clean_activity_access_private_reuse_no_restriction_error(self):
        self.activity1.access = ActivityAccess.PRIVATE.name
        self.activity1.reuse = ActivityReuse.NO_RESTRICTION.name
        with self.assertRaises(ValidationError):
            self.activity1.clean()
