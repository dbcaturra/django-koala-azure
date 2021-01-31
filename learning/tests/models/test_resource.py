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
import os
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from learning.exc import ResourceNotReusableError, ResourceNotReusableOnlyAuthorError
from learning.models import Resource, ResourceAccess, ResourceReuse, Licences, Activity, ActivityAccess, Duration, \
    CollaboratorRole, ResourceCollaborator
from learning.tests.views.test_resource_views import get_temporary_file


class ResourceTestCase(TestCase):

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
            author=get_user_model().objects.get(pk=1),
            language="en"
        )

        self.resource1 = Resource.objects.create(
            author=get_user_model().objects.get(pk=2),
            language="en"
        )


class ResourceUserPermsTest(ResourceTestCase):

    def test_perms_for_connected_user_on_public_resource(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.resource1.access = ResourceAccess.PUBLIC.name
        self.assertEqual(sorted(['view_resource']), sorted(self.resource1.get_user_perms(unknown_user)))

    def test_perms_for_anonymous_user_on_public_resource(self):
        anonymous_user = AnonymousUser()
        self.resource1.access = ResourceAccess.PUBLIC.name
        self.assertEqual(sorted(['view_resource']), sorted(self.resource1.get_user_perms(anonymous_user)))

    def test_perms_for_author_on_public_resource(self):
        user = self.resource1.author
        self.resource1.access = ResourceAccess.PUBLIC.name
        expected_perms = [
            "view_resource", "delete_resource", "add_resource", "change_resource",
            "view_similar_resource", "view_usage_resource",
            "add_collaborator_resource", "view_collaborators_resource", "change_collaborator_resource",
            "delete_collaborator_resource", "toggle_important_question_resource",
            'add_objective_resource',
            'delete_objective_resource',
            'view_objective_resource', 'change_objective_resource',

        ]
        self.assertEqual(sorted(expected_perms), sorted(self.resource1.get_user_perms(user)))

    def test_perms_for_author_on_private_resource(self):
        user = self.resource1.author
        self.resource1.access = ResourceAccess.PRIVATE.name
        expected_perms = [
            "view_resource", "delete_resource", "add_resource", "change_resource",
            "view_similar_resource", "view_usage_resource",
            "add_collaborator_resource", "view_collaborators_resource", "change_collaborator_resource",
            "delete_collaborator_resource", "toggle_important_question_resource",
            'add_objective_resource', 'delete_objective_resource',
            'view_objective_resource', 'change_objective_resource',

        ]
        self.assertEqual(sorted(expected_perms), sorted(self.resource1.get_user_perms(user)))

    def test_perms_for_author_on_existing_activity_resource(self):
        user = self.resource1.author
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        expected_perms = [
            "view_resource", "delete_resource", "add_resource", "change_resource",
            "view_similar_resource", "view_usage_resource",
            "add_collaborator_resource", "view_collaborators_resource", "change_collaborator_resource",
            "delete_collaborator_resource", "toggle_important_question_resource",
            'add_objective_resource', 'delete_objective_resource',
            'view_objective_resource', 'change_objective_resource',

        ]
        self.assertEqual(sorted(expected_perms), sorted(self.resource1.get_user_perms(user)))

    def test_perms_for_connected_on_resource_linked_to_public_activity(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertIn("view_activity", self.activity1.get_user_perms(unknown_user))
        self.activity1.save()

        # Link the resource with the activity
        self.activity1.resources.add(self.resource1)

        self.assertIn("view_resource", self.resource1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_resource_linked_to_public_activity(self):
        anonymous_user = AnonymousUser()
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertIn("view_activity", self.activity1.get_user_perms(anonymous_user))
        self.activity1.save()

        # Link the resource with the activity
        self.activity1.resources.add(self.resource1)

        self.assertIn("view_resource", self.resource1.get_user_perms(anonymous_user))

    def test_perms_for_connected_on_resource_linked_to_private_course(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PRIVATE.name
        self.assertNotIn("view_activity", self.activity1.get_user_perms(unknown_user))
        self.activity1.save()

        # Link the resource with the activity
        self.activity1.resources.add(self.resource1)

        self.assertNotIn("view_resource", self.resource1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_resource_linked_to_private_course(self):
        anonymous_user = AnonymousUser()
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PRIVATE.name
        self.assertNotIn("view_activity", self.activity1.get_user_perms(anonymous_user))
        self.activity1.save()

        # Link the resource with the activity
        self.activity1.resources.add(self.resource1)

        self.assertNotIn("view_resource", self.resource1.get_user_perms(anonymous_user))

    def test_perms_for_connected_on_resource_not_linked_to_public_course(self):
        unknown_user = get_user_model().objects.create_user(id=99, username="unknown")
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(unknown_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertIn("view_activity", self.activity1.get_user_perms(unknown_user))
        self.activity1.save()

        self.assertNotIn("view_resource", self.resource1.get_user_perms(unknown_user))

    def test_perms_for_anonymous_on_resource_not_linked_to_public_course(self):
        anonymous_user = AnonymousUser()
        self.resource1.access = ResourceAccess.EXISTING_ACTIVITIES.name
        self.assertNotIn("view_resource", self.resource1.get_user_perms(anonymous_user))

        # Ensure the user can view the course, this is not what is tested
        self.activity1.access = ActivityAccess.PUBLIC.name
        self.assertIn("view_activity", self.activity1.get_user_perms(anonymous_user))
        self.activity1.save()

        self.assertNotIn("view_resource", self.resource1.get_user_perms(anonymous_user))


class ResourceTest(ResourceTestCase):
    """
    Default values
    """

    def test_default_values_for_attributes(self):
        resource = Resource.objects.create(author=get_user_model().objects.get(pk=1),
                                           name="A sample name to test the ++slug++ generator")
        self.assertEqual(resource.access, ResourceAccess.PUBLIC.name)
        self.assertEqual(resource.reuse, ResourceReuse.ONLY_AUTHOR.name)
        self.assertEqual(resource.licence, Licences.CC_BY.name)
        self.assertEqual(resource.duration, Duration.NOT_SPECIFIED.name)
        self.assertEqual(resource.slug, "a-sample-name-to-test-the-slug-generator")

    """
    Property object_collaborators
    """

    def test_object_collaborators(self):
        ResourceCollaborator.objects.create(
            collaborator=get_user_model().objects.get(pk=1), role=CollaboratorRole.TEACHER.name,
            resource=self.resource1
        )
        self.assertEqual(1, self.resource1.object_collaborators.count())
        self.assertEqual(get_user_model().objects.get(pk=1), self.resource1.object_collaborators.first().collaborator)
        self.assertEqual(CollaboratorRole.TEACHER.name, self.resource1.object_collaborators.first().role)
        self.assertEqual(self.resource1, self.resource1.object_collaborators.first().resource)

    """
    Method is_reusable
    """

    def test_is_reusable_activity_not_reusable_error(self):
        self.resource1.reuse = ResourceReuse.NON_REUSABLE.name
        with self.assertRaises(ResourceNotReusableError):
            self.resource1.is_reusable()

    def test_is_reusable_activity_only_author_error(self):
        unknown_user = get_user_model().objects.create_user(username="unknown_user")
        self.resource1.reuse = ResourceReuse.ONLY_AUTHOR.name
        self.activity1.author = unknown_user
        with self.assertRaises(ResourceNotReusableOnlyAuthorError):
            self.resource1.is_reusable(for_activity=self.activity1)

    def test_is_reusable_activity_only_author_missing_parameter(self):
        self.resource1.reuse = ResourceReuse.ONLY_AUTHOR.name
        with self.assertRaises(RuntimeError):
            self.resource1.is_reusable()

    def test_is_reusable_activity_no_restriction(self):
        self.resource1.reuse = ResourceReuse.NO_RESTRICTION.name
        self.assertTrue(self.resource1.is_reusable())

    """
    Method clean
    """

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_clean_attachment_larger_than_default(self):
        self.resource1.attachment.save(
            "sample_update.txt", get_temporary_file(file_size=2 ** 21), save=True
        )
        self.resource1.save()
        self.assertIsNotNone(self.resource1.attachment.name)
        self.assertIn("sample_update", self.resource1.attachment.name)
        attachment_path = self.resource1.attachment.path
        self.assertTrue(os.path.isfile(attachment_path))
        with self.assertRaises(ValidationError):
            self.resource1.clean()

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_clean_attachment_size_equals_default(self):
        self.resource1.attachment.save(
            "sample_update.txt", get_temporary_file(file_size=2 ** 20), save=True
        )
        self.resource1.save()
        self.assertIsNotNone(self.resource1.attachment.name)
        self.assertIn("sample_update", self.resource1.attachment.name)
        attachment_path = self.resource1.attachment.path
        self.assertTrue(os.path.isfile(attachment_path))
        self.resource1.clean()

    @override_settings(LEARNING_UPLOAD_SIZE=2 ** 15)
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_clean_attachment_larger_than_in_settings(self):
        self.resource1.attachment.save(
            "sample_update.txt", get_temporary_file(file_size=2 ** 16), save=True
        )
        self.resource1.save()
        self.assertIsNotNone(self.resource1.attachment.name)
        self.assertIn("sample_update", self.resource1.attachment.name)
        attachment_path = self.resource1.attachment.path
        self.assertTrue(os.path.isfile(attachment_path))
        with self.assertRaises(ValidationError):
            self.resource1.clean()

    @override_settings(LEARNING_UPLOAD_SIZE=2 ** 15)
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_clean_attachment_size_equals_settings(self):
        self.resource1.attachment.save(
            "sample_update.txt", get_temporary_file(file_size=2 ** 15), save=True
        )
        self.resource1.save()
        self.assertIsNotNone(self.resource1.attachment.name)
        self.assertIn("sample_update", self.resource1.attachment.name)
        attachment_path = self.resource1.attachment.path
        self.assertTrue(os.path.isfile(attachment_path))
        self.resource1.clean()

    def test_clean_no_attachment(self):
        self.resource1.attachment = None
        self.resource1.clean()

    def test_clean_resource_access_private_reuse_no_restriction(self):
        self.resource1.access = ResourceAccess.PRIVATE.name
        self.resource1.reuse = ResourceReuse.NO_RESTRICTION.name
        with self.assertRaises(ValidationError):
            self.resource1.clean()

    def test_clean_resource_licence_na_reuse_no_restriction(self):
        self.resource1.access = ResourceAccess.PUBLIC.name
        self.resource1.licence = Licences.NA.name
        self.resource1.reuse = ResourceReuse.NO_RESTRICTION.name
        with self.assertRaises(ValidationError):
            self.resource1.clean()

    def test_clean_resource_licence_all_rights_reserved_reuse_no_restriction(self):
        self.resource1.access = ResourceAccess.PUBLIC.name
        self.resource1.licence = Licences.NA.name
        self.resource1.reuse = ResourceReuse.NO_RESTRICTION.name
        with self.assertRaises(ValidationError):
            self.resource1.clean()

    def test_clean_resource_licence_ok_reuse_no_restriction(self):
        self.resource1.access = ResourceAccess.PUBLIC.name
        self.resource1.reuse = ResourceReuse.NO_RESTRICTION.name
        for licence in [Licences.CC_0, Licences.CC_BY, Licences.CC_BY_SA,
                        Licences.CC_BY_NC, Licences.CC_BY_NC_SA, Licences.CC_BY_ND,
                        Licences.CC_BY_NC_ND]:
            self.resource1.licence = licence.name
            self.resource1.clean()

    """
    Method delete
    """

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_delete_resource_also_delete_related_attachment(self):
        self.resource1.attachment.save(
            "sample_update.txt", get_temporary_file(), save=True
        )
        self.resource1.save()
        self.assertIsNotNone(self.resource1.attachment.name)
        self.assertIn("sample_update", self.resource1.attachment.name)
        self.assertTrue(os.path.isfile(self.resource1.attachment.path))
        self.resource1.delete()
        self.assertFalse(os.path.isfile(self.resource1.attachment.path))
