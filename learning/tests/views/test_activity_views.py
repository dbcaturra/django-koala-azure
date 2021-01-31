#
# Copyright (C) 2019 Guillaume Bernard <guillaume.bernard@koala-lms.org>

# Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
# Copyright (C) 2020 Nolwenn Machon <nolwenn.machon@etudiant.univ-lr.fr>
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
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from learning.forms import BasicSearchForm
from learning.models import Resource, ResourceAccess, ResourceReuse, Activity, ActivityAccess, ActivityReuse, Course, \
    CourseActivity, Duration, Licences, ResourceType
from learning.tests.views.helpers import ClientFactory
from learning.tests.views.test_resource_views import get_temporary_file


class ActivityViews(TestCase):

    def setUp(self):
        for initials in ["ws", "acd", "lt", "ed"]:
            setattr(self, initials, get_user_model().objects.create_user(username=initials, password="pwd"))

        self.anon_client = Client()

        self.ws_activity = Activity.objects.create(
            id=1,
            name="A sample activity",
            description="A sample description",
            access=ResourceAccess.PUBLIC.name,
            reuse=ResourceReuse.NO_RESTRICTION.name,
            author=self.ws,
            language="en",
        )

        self.acd_activity = Activity.objects.create(author=self.acd, name="activity1", language="en")
        self.lt_activity = Activity.objects.create(author=self.lt, name="activity2", language="en")

        self.resource1 = Resource.objects.create(
            id=1,
            name="resource1",
            author=self.ws,
            language="en"
        )

    """
    ActivityDetailView
    """

    def test_get_resource_view(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(200, response.status_code)
        the_object = response.context.get('object')
        activity = response.context.get('activity')
        self.assertEqual(the_object, self.ws_activity)
        self.assertEqual(activity, self.ws_activity)
        self.assertTemplateUsed(response, "learning/activity/detail.html")

    def test_post_detail_resource_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_activity_view_as_author_private_resource_no_resource(self):
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "link-activity-usage", count=1)
        self.assertContains(response, "link-activity-similar", count=1)
        self.assertContains(response, "link-activity-add-resource", count=2)
        self.assertContains(response, "link-activity-attach-resource", count=1)
        self.assertContains(response, "btn-change-activity", count=1)
        self.assertContains(response, "btn-delete-activity", count=1)
        self.assertContains(response, "activity-no-resource", count=2)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)

    def test_get_detail_activity_view_as_author_private_resource_one_resource(self):
        self.ws_activity.resources.add(self.resource1)
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "link-activity-usage", count=1)
        self.assertContains(response, "link-activity-similar", count=1)
        self.assertContains(response, "link-activity-add-resource", count=2)
        self.assertContains(response, "link-activity-attach-resource", count=1)
        self.assertContains(response, "btn-change-activity", count=1)
        self.assertContains(response, "btn-delete-activity", count=1)
        self.assertNotContains(response, "activity-no-resource")
        activity = response.context.get('activity')
        self.assertContains(response, "resource-block-for-{}".format(self.resource1.slug))
        self.assertEqual(activity, self.ws_activity)

    def test_get_detail_activity_view_registered_user_private_activity(self):
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn("view_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_activity_view_registered_user_public_activity(self):
        self.ws_activity.resources.add(self.resource1)
        self.ws_activity.access = ActivityAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, "link-activity-usage")
        self.assertNotContains(response, "link-activity-similar")
        self.assertNotContains(response, "link-activity-add-resource")
        self.assertNotContains(response, "btn-change-activity")
        self.assertNotContains(response, "btn-delete-activity")
        self.assertNotContains(response, "activity-no-resource")
        activity = response.context.get('activity')
        self.assertContains(response, "resource-block-for-{}".format(self.resource1.slug))
        self.assertEqual(activity, self.ws_activity)

    """
    ActivityCreateView
    """

    def test_get_create_activity_view(self):
        response = ClientFactory.get_client_for_user("ws").get(reverse("learning:activity/add"))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/add.html")

    def test_post_create_activity_error_missing_tags_name_description_language(self):
        form_data = {
            'reuse': ActivityReuse.NO_RESTRICTION.name,
            'access': ActivityAccess.PUBLIC.name
        }
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:activity/add"), form_data)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/add.html")
        self.assertContains(response, "is-invalid", count=4)

    def test_post_create_activity_error_missing_all_fields(self):
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:activity/add"))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/add.html")
        self.assertContains(response, "is-invalid", count=6)

    def test_post_create_activity(self):
        form_data = {
            'name': "A sample name",
            'description': "A short description",
            'language': 'fr',
            'reuse': ActivityReuse.NO_RESTRICTION.name,
            'access': ActivityAccess.PUBLIC.name,
            'tags': "A",
        }
        response = ClientFactory.get_client_for_user("ws").post(reverse("learning:activity/add"), form_data)
        # Check redirection after resource creation
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/detail", kwargs={'slug': "a-sample-name"})
        )
        # The author is the request sender
        resource = Activity.objects.get(pk=4)
        self.assertEqual(self.ws, resource.author)

    """
    ActivityUpdateView
    """

    def test_update_get_activity_as_author(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/update", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/details/change.html")

    def test_update_post_activity_as_author(self):
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
            'language': 'fr',
            'access': ActivityAccess.PUBLIC.name,
            'reuse': ActivityReuse.ONLY_AUTHOR.name,
            'tags': "A"
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/update", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        self.assertRedirects(
            response, status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/detail", kwargs={'slug': "a-sample-name-that-changed"})
        )

    def test_update_post_activity_as_author_errors(self):
        form_data = {
            'name': "",
            'description': "",
            'language': 'fakelanguage',
            'access': ActivityAccess.PUBLIC.name,
            'reuse': ActivityReuse.ONLY_AUTHOR.name,
            'tags': "A"
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/update", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "is-invalid", count=3)

    def test_update_get_activity_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/update", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_update_post_activity_without_being_author_forbidden(self):
        form_data = {
            'name': "A sample name that changed",
            'description': "A short description",
        }
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:activity/update", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        self.assertEqual(403, response.status_code)

    """
    ActivityDeleteView
    """

    def test_delete_activity_get_as_author(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/delete", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/delete.html")

    def test_delete_resource_post_as_author(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/delete", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/my")
        )
        with self.assertRaises(ObjectDoesNotExist):
            Activity.objects.get(pk=self.ws_activity.id)

    def test_delete_resource_get_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/delete", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_delete_activity_post_without_being_author_forbidden(self):
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:activity/delete", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    """
    ActivityDetailUsageView
    """

    def test_post_detail_usage_activity_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_usage_activity_view_as_author_private_not_used(self):
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_usage_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertNotContains(response, "table-activity-usage")
        self.assertContains(response, "alert-not-used")

    def test_get_detail_usage_activity_view_as_author_public_not_used(self):
        self.ws_activity.access = ResourceAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_usage_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertNotContains(response, "table-activity-usage")
        self.assertContains(response, "alert-not-used")

    def test_get_detail_usage_activity_view_as_author_public_resource_used_twice(self):
        c1 = Course.objects.create(author=self.ws, name="test1", language="en")
        c2 = Course.objects.create(author=self.acd, name="test2", language="en")
        CourseActivity.objects.create(activity=self.ws_activity, rank=1, course=c1)
        CourseActivity.objects.create(activity=self.ws_activity, rank=1, course=c2)
        self.assertEqual(2, self.ws_activity.course_activities.count())
        self.ws_activity.access = ResourceAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_usage_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertContains(response, "table-activity-usage")
        self.assertContains(response, "usage-activity-row", count=2)
        self.assertNotContains(response, "alert-not-used")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(2, len(page_obj.object_list))

    def test_get_detail_usage_activity_view_as_author_private_resource_used_three_times(self):
        c1 = Course.objects.create(author=self.ws, name="test1", language="en")
        c2 = Course.objects.create(author=self.acd, name="test2", language="en")
        c3 = Course.objects.create(author=self.acd, name="test3", language="en")
        CourseActivity.objects.create(activity=self.ws_activity, rank=1, course=c1)
        CourseActivity.objects.create(activity=self.ws_activity, rank=1, course=c2)
        CourseActivity.objects.create(activity=self.ws_activity, rank=1, course=c3)
        self.assertEqual(3, self.ws_activity.course_activities.count())
        self.ws_activity.access = ResourceAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_usage_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertIsNotNone(activity)
        self.assertEqual(activity, self.ws_activity)
        self.assertContains(response, "table-activity-usage")
        self.assertContains(response, "usage-activity-row", count=3)
        self.assertNotContains(response, "alert-not-used")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(3, len(page_obj.object_list))

    def test_get_detail_usage_activity_view_user_private_resource_forbidden(self):
        self.ws_activity.access = ResourceAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn("view_usage_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_usage_resource_view_user_public_resource(self):
        self.ws_activity.access = ResourceAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/usage", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn("view_usage_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    """
    activityDetailSimilarView
    """

    def test_post_detail_similar_activity_view_method_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_get_detail_similar_activity_view_as_author_private_activity_empty(self):
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_similar_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertNotContains(response, "similar-activities")
        self.assertContains(response, "alert-no-similar-activity")

    def test_get_detail_similar_activity_view_as_author_public_activity_empty(self):
        self.ws_activity.access = ActivityAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_similar_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertNotContains(response, "similar-activities")
        self.assertContains(response, "alert-no-similar-activity")

    def test_get_detail_similar_activity_view_as_author_public_activity_used_twice(self):
        self.ws_activity.tags.add("tag1")
        self.ws_activity.tags.add("tag2")
        for tag in self.ws_activity.tags.all():
            self.acd_activity.tags.add(tag)
            self.lt_activity.tags.add(tag)
        self.acd_activity.save()
        self.lt_activity.save()
        self.ws_activity.access = ActivityAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn("view_similar_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(200, response.status_code)
        activity = response.context.get('activity')
        self.assertEqual(activity, self.ws_activity)
        self.assertNotContains(response, "alert-no-similar-activity")
        self.assertContains(response, "similar-activities")
        page_obj = response.context.get('page_obj')
        self.assertIsNotNone(page_obj)
        self.assertEqual(2, len(page_obj.object_list))

    def test_get_detail_similar_activity_view_user_private_activity_forbidden(self):
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn("view_similar_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    def test_get_detail_similar_activity_view_user_public_activity(self):
        self.ws_activity.access = ActivityAccess.PUBLIC.name
        self.ws_activity.save()
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/similar", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn("view_similar_activity", self.ws_activity.get_user_perms(self.acd))
        self.assertEqual(403, response.status_code)

    """
    ResourceOnActivityDetailView
    """

    def test_get_resource_on_activity(self):
        r1 = Resource.objects.create(author=self.ws, name="A first resource", language="en")
        self.ws_activity.resources.add(r1)
        response = ClientFactory.get_client_for_user("ws").get(
            reverse(
                "learning:activity/resource/detail",
                kwargs={'slug': self.ws_activity.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.ws_activity.name, count=3)
        self.assertContains(response, "A first resource", count=3)
        self.assertEqual(self.ws_activity, response.context.get('object'))
        self.assertEqual(self.ws_activity, response.context.get('activity'))
        self.assertEqual(r1, response.context.get('resource'))

    def test_get_resource_on_activity_no_perm_on_resource(self):
        r1 = Resource.objects.create(
            author=self.acd, name="A first resource", access=ResourceAccess.PRIVATE.name, language="en"
        )
        self.ws_activity.resources.add(r1)
        self.assertNotIn("view_resource", r1.get_user_perms(self.ws))
        self.assertIn("view_activity", self.ws_activity.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse(
                "learning:activity/resource/detail",
                kwargs={'slug': self.ws_activity.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(403, response.status_code)

    def test_get_resource_on_activity_no_perm_on_activity(self):
        r1 = Resource.objects.create(
            author=self.acd, name="A first resource", access=ResourceAccess.PUBLIC.name, language="en"
        )
        self.ws_activity.author = self.acd
        self.ws_activity.access = ActivityAccess.PRIVATE.name
        self.ws_activity.save()
        self.ws_activity.resources.add(r1)
        self.assertIn("view_resource", r1.get_user_perms(self.ws))
        self.assertNotIn("view_activity", self.ws_activity.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse(
                "learning:activity/resource/detail",
                kwargs={'slug': self.ws_activity.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(403, response.status_code)

    """
    ActivityCreateResourceView
    """

    def test_get_create_resource_on_activity_as_author(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/activity/details/add_resource.html")

    def test_get_create_resource_on_activity_no_perm(self):
        self.assertNotIn("change_activity", self.ws_activity.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_post_create_resource_on_activity_no_perm(self):
        self.assertNotIn("change_activity", self.ws_activity.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_create_resource_on_activity_as_author(self):
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
            "media": get_temporary_file()
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        resource = Resource.objects.get(slug="a-sample-name")
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:resource/detail", kwargs={'slug': resource.slug})
        )
        self.assertIsNotNone(resource)
        self.assertEqual(1, resource.activities.count())
        self.assertIn(resource, self.ws_activity.resources.all())
        self.assertEqual(resource.author, self.ws)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_create_resource_on_activity_as_author_not_reusable_resource_not_saved(self):
        form_data = {
            'name': "A sample name",
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.NON_REUSABLE.name,
            'duration': Duration.NOT_SPECIFIED.name,
            'tags': "A",
            "media": get_temporary_file()
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(Resource.objects.filter(name="A sample name").exists())
        self.assertEqual(0, self.ws_activity.resources.count())
        self.assertEqual(0, len(response.context.get('form').errors.as_data()))
        self.assertEqual(0, self.ws_activity.resources.count())

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_post_create_resource_on_activity_invalid_form(self):
        form_data = {
            'description': "A short description",
            'type': ResourceType.FILE.name,
            'language': 'fr',
            'licence': Licences.CC_BY.name,
            'access': ResourceAccess.PUBLIC.name,
            'reuse': ResourceReuse.NO_RESTRICTION.name,
            'duration': Duration.NOT_SPECIFIED.name,
            'tags': "A",
            "media": get_temporary_file()
        }
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/resource/add", kwargs={'slug': self.ws_activity.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(Resource.objects.filter(name="A sample name").exists())
        self.assertEqual(0, self.ws_activity.resources.count())
        self.assertEqual(1, len(response.context.get('form').errors.as_data()))
        self.assertEqual(0, self.ws_activity.resources.count())

    """
    ResourceUnlinkOnActivityView
    """

    def test_unlink_on_activity_no_perm(self):
        self.assertNotIn("change_activity", self.ws_activity.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/resource/unlink", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_get_unlink_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/resource/unlink", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )

    def test_post_unlink_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        r1 = Resource.objects.create(name="A sample resource", author=self.acd, language="en")
        self.ws_activity.resources.add(r1)
        self.assertIn(r1, self.ws_activity.resources.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse(
                "learning:activity/detail/resource/unlink",
                kwargs={'slug': self.ws_activity.slug, },
            ),
            {'resource': r1.id}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/detail", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertNotIn(r1, self.ws_activity.resources.all())

    def test_post_unlink_resource_not_linked_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        r1 = Resource.objects.create(name="A sample resource", author=self.acd, language="en")
        r2 = Resource.objects.create(name="A sample resource 2", author=self.lt, language="en")
        self.ws_activity.resources.add(r1)
        self.assertIn(r1, self.ws_activity.resources.all())
        self.assertNotIn(r2, self.ws_activity.resources.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse(
                "learning:activity/detail/resource/unlink",
                kwargs={'slug': self.ws_activity.slug, },
            ),
            {'resource': r2.id}
        )
        self.assertEqual(302, response.status_code)
        self.assertIn(r1, self.ws_activity.resources.all())
        self.assertNotIn(r2, self.ws_activity.resources.all())

    def test_post_unlink_does_not_exist_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        r1 = Resource.objects.create(name="A sample resource", author=self.acd)
        self.ws_activity.resources.add(r1)
        self.assertIn(r1, self.ws_activity.resources.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse(
                "learning:activity/detail/resource/unlink",
                kwargs={'slug': self.ws_activity.slug, },
            ),
            {'resource': r1.id + 1}
        )
        self.assertEqual(404, response.status_code)
        self.assertIn(r1, self.ws_activity.resources.all())

    """
    ResourceAttachOnActivityView
    """

    def test_attach_on_activity_no_perm(self):
        self.assertNotIn("change_activity", self.ws_activity.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:activity/detail/resource/attach", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_get_attach_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:activity/detail/resource/attach", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed("learning/activity/details/attach_resource.html")
        self.assertIsNotNone(response.context.get('form'))
        self.assertIsInstance(response.context.get('form'), BasicSearchForm)

    def test_post_attach_on_activity_view(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        r1 = Resource.objects.create(
            name="A sample resource", author=self.acd,
            reuse=ResourceReuse.NO_RESTRICTION.name, language="en"
        )
        self.assertTrue(r1.is_reusable(self.ws_activity))
        self.assertNotIn(r1, self.ws_activity.resources.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/resource/attach", kwargs={'slug': self.ws_activity.slug}),
            {'resource': r1.id}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:activity/detail/resource/attach", kwargs={'slug': self.ws_activity.slug})
        )
        self.assertIn(r1, self.ws_activity.resources.all())

    def test_post_attach_on_activity_view_not_exists(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        self.assertEqual(0, self.ws_activity.resources.count())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:activity/detail/resource/attach", kwargs={'slug': self.ws_activity.slug}),
            {'resource': 99}
        )
        self.assertEqual(404, response.status_code)
        self.assertEqual(0, self.ws_activity.resources.count())

    def test_post_attach_on_activity_view_already_linked(self):
        self.assertIn("change_activity", self.ws_activity.get_user_perms(self.ws))
        r1 = Resource.objects.create(name="A sample resource", author=self.acd, language="en")
        r2 = Resource.objects.create(name="A sample resource 2", author=self.lt, language="en")
        self.ws_activity.resources.add(r1)
        self.assertIn(r1, self.ws_activity.resources.all())
        self.assertNotIn(r2, self.ws_activity.resources.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse(
                "learning:activity/detail/resource/attach",
                kwargs={'slug': self.ws_activity.slug, },
            ),
            {'resource': r1.id}
        )
        self.assertEqual(302, response.status_code)
        self.assertIn(r1, self.ws_activity.resources.all())
        self.assertNotIn(r2, self.ws_activity.resources.all())
