#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>
# Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
# Copyright (C) 2020 Louis Barbier <louis.barbier41@outlook.fr>
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
import os
import tempfile
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import filesizeformat
from django.test import TestCase, override_settings
from django.urls import reverse

from learning.models import Resource, ResourceType, Licences, ResourceAccess, ResourceReuse, Duration, Activity
from learning.tests.views.helpers import ClientFactory


def get_temporary_file(file_size=2 ** 20):
    file_path = tempfile.mkstemp()[1]
    with open(file_path, mode="wb") as file:
        file.write(os.getrandom(file_size, os.GRND_NONBLOCK))
    return open(file_path, mode="rb")


class ResourceViews(TestCase):

    def setUp(self):
        for initials in ["ws", "acd", "lt"]:
            setattr(self, initials, get_user_model().objects.create_user(username=initials, password="pwd"))

        self.ws_resource = Resource.objects.create(
            id=1,
            name="A sample resource",
            description="A sample description",
            type=ResourceType.AUDIO,
            access=ResourceAccess.PUBLIC.name,
            reuse=ResourceReuse.NO_RESTRICTION.name,
            duration=Duration.NOT_SPECIFIED.name,
            licence=Licences.CC_0.name,
            author=self.ws,
            language='fr',
        )
        self.ws_resource.tags.add("A")
        self.ws_resource.tags.add("B")

        self.acd_resource = Resource.objects.create(author=self.acd, name="resource1", language="en")
        self.lt_resource = Resource.objects.create(author=self.lt, name="resource2", language="en")

    """
    ResourceDetailView
    """

    def test_get_resource_view(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(200, response.status_code)
        the_object = response.context.get('object')
        resource = response.context.get('resource')
        self.assertEqual(the_object, self.ws_resource)
        self.assertEqual(resource, self.ws_resource)
        self.assertTemplateUsed(response, "learning/resource/detail.html")

    def common_contains_resource_detail_view(self, response):
        self.assertContains(response, "object-tags", count=1)
        self.assertContains(response, "object-language", count=1)
        self.assertContains(response, "resource-description", count=1)
        the_object = response.context.get('object')
        resource = response.context.get('resource')
        self.assertIsNotNone(the_object)
        self.assertIsNotNone(resource)

    def test_post_detail_resource_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_resource_view_as_author_private_resource(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "access-badge", count=1)
        self.assertContains(response, "reuse-badge", count=1)
        self.assertContains(response, "licence-badge", count=1)
        self.assertContains(response, "duration-badge", count=1)
        self.assertContains(response, "btn-edit-resource", count=1)
        self.assertContains(response, "btn-delete-resource", count=1)
        self.assertContains(response, "link-resource-detail", count=1)
        self.assertContains(response, "link-resource-usage", count=1)
        self.assertContains(response, "link-resource-similar", count=1)
        self.assertNotContains(response, "attachment-description")
        self.common_contains_resource_detail_view(response)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_get_detail_resource_view_as_author_public_resource(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "access-badge", count=1)
        self.assertContains(response, "reuse-badge", count=1)
        self.assertContains(response, "licence-badge", count=1)
        self.assertContains(response, "duration-badge", count=1)
        self.assertContains(response, "btn-edit-resource", count=1)
        self.assertContains(response, "btn-delete-resource", count=1)
        self.assertContains(response, "link-resource-detail", count=1)
        self.assertContains(response, "link-resource-usage", count=1)
        self.assertContains(response, "link-resource-similar", count=1)
        self.assertContains(response, "media-description")
        self.common_contains_resource_detail_view(response)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertIsNotNone(resource.attachment.name)
        self.assertEqual(os.path.join("resources", str(self.ws_resource.id), filename),  resource.attachment.name)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_get_detail_resource_view_as_author_public_resource_no_attachment(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "access-badge", count=1)
        self.assertContains(response, "reuse-badge", count=1)
        self.assertContains(response, "licence-badge", count=1)
        self.assertContains(response, "duration-badge", count=1)
        self.assertContains(response, "btn-edit-resource", count=1)
        self.assertContains(response, "btn-delete-resource", count=1)
        self.assertContains(response, "link-resource-detail", count=1)
        self.assertContains(response, "link-resource-usage", count=1)
        self.assertContains(response, "link-resource-similar", count=1)
        self.assertNotContains(response, "attachment-description")
        self.common_contains_resource_detail_view(response)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)

    def test_get_detail_resource_view_user_private_resource_forbidden(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertNotIn("view_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_resource_view_user_public_resource(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, "access-badge")
        self.assertNotContains(response, "reuse-badge")
        self.assertNotContains(response, "licence-badge")
        self.assertNotContains(response, "duration-badge")
        self.assertNotContains(response, "btn-edit-resource")
        self.assertNotContains(response, "btn-delete-resource")
        self.assertContains(response, "link-resource-detail", count=1)
        self.assertNotContains(response, "link-resource-usage")
        self.assertNotContains(response, "link-resource-similar")
        self.assertNotContains(response, "attachment-description")
        self.common_contains_resource_detail_view(response)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)

    """
    ResourceCreateView
    """

    def test_get_create_resource_view(self):
        response = ClientFactory.get_client_for_user("ws").get(reverse("learning:resource/add"))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/add.html")
        self.assertContains(response, """id="resource_add_form" enctype=\"multipart/form-data\"""")

    def test_post_create_resource_error_missing_tags_name_description_language(self):
        form_data = {
            'type': ResourceType.FILE.name,
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
        }
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:resource/add"), form_data)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/add.html")
        self.assertContains(response, "is-invalid", count=4)

    def test_post_create_resource_error_missing_all_fields(self):
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:resource/add"))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/add.html")
        self.assertContains(response, "is-invalid", count=9)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_create_resource(self):
        temp_file = get_temporary_file()
        form_data = {
            'name': "A sample name",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
            'tags': "A",
            "attachment": temp_file
        }
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:resource/add"), form_data)
        # Check redirection after resource creation
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/detail", kwargs={'slug': "a-sample-name"})
        )
        # The author is the request sender
        resource = Resource.objects.get(pk=4)
        self.assertEqual(self.ws, resource.author)
        self.assertIsNotNone(resource.attachment.name)
        self.assertIn(os.path.basename(temp_file.name), resource.attachment.name)
        self.assertTrue(os.path.isfile(resource.attachment.path))

    """
    ResourceUpdateView
    """

    def test_update_get_resource_as_author(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/details/change.html")
        self.assertContains(response, """id="resource_update_form" enctype=\"multipart/form-data\"""")

    def test_update_get_resource_form_without_attachment(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/details/change.html")
        self.assertNotContains(response, "column-clear-attachment")
        self.assertNotContains(response, "column-download-attachment")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_update_get_resource_form_with_attachment(self):
        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/details/change.html")
        self.assertContains(response, "column-clear-attachment")
        self.assertContains(response, "column-download-attachment")

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_update_post_resource_as_author(self):
        self.assertIsNone(self.ws_resource.attachment.name)

        temp_file = get_temporary_file()
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
            "tags": "B",
            "attachment": temp_file
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug}), form_data
        )
        self.assertRedirects(
            response, status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/detail", kwargs={'slug': "a-sample-name-that-changed"})
        )
        resource = Resource.objects.get(pk=self.ws_resource.id)
        self.assertIsNotNone(resource.attachment.name)
        self.assertIn(os.path.basename(temp_file.name), resource.attachment.name)
        self.assertTrue(os.path.isfile(resource.attachment.path))

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_update_post_resource_as_author_replace_attachment(self):
        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))

        temp_file = get_temporary_file(file_size=2 ** 5)
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
            "tags": "B",
            "attachment": temp_file
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug}), form_data
        )
        self.assertRedirects(
            response, status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/detail", kwargs={'slug': "a-sample-name-that-changed"})
        )
        resource = Resource.objects.get(pk=self.ws_resource.id)
        self.assertIsNotNone(resource.attachment.name)
        self.assertIn(os.path.basename(temp_file.name), resource.attachment.name)

        # Current file exists and previous has been removed
        self.assertTrue(os.path.isfile(resource.attachment.path))
        self.assertFalse(os.path.isfile(os.path.join(settings.MEDIA_ROOT, filename)))

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_update_post_resource_as_author_delete_attachment(self):
        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
            "tags": "B",
            "attachment-clear": "on"
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug}), form_data
        )
        self.assertRedirects(
            response, status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/detail", kwargs={'slug': "a-sample-name-that-changed"})
        )
        resource = Resource.objects.get(pk=self.ws_resource.id)
        self.assertEqual("", resource.attachment.name)
        self.assertFalse(os.path.isfile(os.path.join(settings.MEDIA_ROOT, filename)))

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_update_post_resource_as_author_too_big_resource(self):

        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))

        resource = Resource.objects.get(pk=self.ws_resource.id)
        self.assertIsNotNone(resource.attachment.name)
        self.assertIn("sample_update", resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))

        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
            "tags": "B",
            "attachment": get_temporary_file(file_size=2 ** 21)
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertIsNotNone(response.context.get('form').errors)
        self.assertContains(response, "sample_update", count=2)  # link and title
        self.assertContains(response, filesizeformat(2 ** 21), count=1)

        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))

        resource = Resource.objects.get(pk=self.ws_resource.id)
        self.assertIsNotNone(resource.attachment.name)
        self.assertIn("sample_update", resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))

    def test_update_get_resource_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_update_post_resource_without_being_author_forbidden(self):
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.ONLY_AUTHOR.name,
            'duration': Duration.NOT_SPECIFIED.name,
        }
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:resource/update", kwargs={'slug': self.ws_resource.slug}), form_data
        )
        self.assertEqual(403, response.status_code)

    """
    ResourceDeleteView
    """

    def test_delete_resource_get_as_author(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/delete", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/resource/delete.html")

    def test_delete_resource_post_as_author(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/delete", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/my")
        )
        with self.assertRaises(ObjectDoesNotExist):
            Resource.objects.get(pk=self.ws_resource.id)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_delete_resource_post_as_author_with_attachment(self):
        filename = "sample_update_{date}.txt".format(date=datetime.now().timestamp())
        self.ws_resource.attachment.save(filename, get_temporary_file(), save=True)
        self.ws_resource.save()
        self.assertIsNotNone(self.ws_resource.attachment.name)
        self.assertIn("sample_update", self.ws_resource.attachment.name)
        self.assertTrue(os.path.isfile(os.path.join(settings.MEDIA_ROOT, "resources", str(self.ws_resource.id), filename)))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/delete", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/my")
        )
        self.assertFalse(os.path.isfile(os.path.join(settings.MEDIA_ROOT, filename)))

    def test_delete_resource_get_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/delete", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_delete_resource_post_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:resource/delete", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(403, response.status_code)

    """
    ResourceDetailUsageView
    """

    def test_post_detail_usage_resource_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_usage_resource_view_as_author_private_resource_empty(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_usage_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertNotContains(response, "table-resource-usage")
        self.assertContains(response, "alert-not-used")

    def test_get_detail_usage_resource_view_as_author_public_resource_empty(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_usage_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertNotContains(response, "table-resource-usage")
        self.assertContains(response, "alert-not-used")

    def test_get_detail_usage_resource_view_as_author_public_resource_used_twice(self):
        a1 = Activity.objects.create(author=self.ws, name="test1")
        a2 = Activity.objects.create(author=self.acd, name="test2")
        a1.resources.add(self.ws_resource)
        a2.resources.add(self.ws_resource)
        self.assertEqual(2, self.ws_resource.activities.count())
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_usage_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertContains(response, "table-resource-usage")
        self.assertContains(response, "usage-activity-row", count=2)
        self.assertNotContains(response, "alert-not-used")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(2, len(page_obj.object_list))

    def test_get_detail_usage_resource_view_as_author_private_resource_used_three_times(self):
        a1 = Activity.objects.create(author=self.ws, name="test1")
        a2 = Activity.objects.create(author=self.acd, name="test2")
        a3 = Activity.objects.create(author=self.lt, name="test3")
        a1.resources.add(self.ws_resource)
        a2.resources.add(self.ws_resource)
        a3.resources.add(self.ws_resource)
        self.assertEqual(3, self.ws_resource.activities.count())
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_usage_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertIsNotNone(resource)
        self.assertEqual(resource, self.ws_resource)
        self.assertContains(response, "table-resource-usage")
        self.assertContains(response, "usage-activity-row", count=3)
        self.assertNotContains(response, "alert-not-used")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(3, len(page_obj.object_list))

    def test_get_detail_usage_resource_view_user_private_resource_forbidden(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertNotIn("view_usage_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_usage_resource_view_user_public_resource(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail/usage", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertNotIn("view_usage_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    """
    ResourceDetailSimilarView
    """

    def test_post_detail_similar_resource_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_similar_resource_view_as_author_private_resource_empty(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_similar_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertNotContains(response, "similar-resources")
        self.assertContains(response, "alert-no-similar-resource")

    def test_get_detail_similar_resource_view_as_author_public_resource_empty(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_similar_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertNotContains(response, "similar-resources")
        self.assertContains(response, "alert-no-similar-resource")

    def test_get_detail_similar_resource_view_as_author_public_resource_used_twice(self):
        for tag in self.ws_resource.tags.all():
            self.acd_resource.tags.add(tag)
            self.lt_resource.tags.add(tag)
        self.acd_resource.save()
        self.lt_resource.save()
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertIn("view_similar_resource", self.ws_resource.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        resource = response.context.get('resource')
        self.assertEqual(resource, self.ws_resource)
        self.assertNotContains(response, "alert-no-similar-resource")
        self.assertContains(response, "similar-resources")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(2, len(page_obj.object_list))

    def test_get_detail_similar_resource_view_user_private_resource_forbidden(self):
        self.ws_resource.access = ResourceAccess.PRIVATE.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertNotIn("view_similar_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_similar_resource_view_user_public_resource(self):
        self.ws_resource.access = ResourceAccess.PUBLIC.name
        self.ws_resource.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:resource/detail/similar", kwargs={'slug': self.ws_resource.slug})
        )
        self.assertNotIn("view_similar_resource", self.ws_resource.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)
