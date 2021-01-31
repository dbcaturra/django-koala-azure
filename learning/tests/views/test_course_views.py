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
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, Client
from django.urls import reverse

from learning.forms import BasicSearchForm
from learning.models import Course, CourseAccess, CourseState, CourseCollaborator, CollaboratorRole, Activity, \
    CourseActivity, ActivityAccess, Resource, ActivityReuse, RegistrationOnCourse
from learning.tests.views.helpers import ClientFactory


class CourseViews(TestCase):
    user_class = get_user_model()

    def setUp(self):
        for initials in ["ws", "acd", "lt", "ed"]:
            setattr(self, initials, get_user_model().objects.create_user(username=initials, password="pwd"))

        self.private_course = Course.objects.create(
            id=1,
            name="A simple course",
            description="A simple description",
            author=self.user_class.objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PRIVATE.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.public_course = Course.objects.create(
            id=2,
            name="A simple course",
            description="A simple description",
            author=self.user_class.objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PUBLIC.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.students_only_course = Course.objects.create(
            id=3,
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.STUDENTS_ONLY.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.collaborators_only_course = Course.objects.create(
            id=4,
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.COLLABORATORS_ONLY.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.activity1 = Activity.objects.create(
            id=1,
            name="An activity 1",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            access=ActivityAccess.PUBLIC.name,
            language="en"
        )
        self.activity2 = Activity.objects.create(
            id=2,
            name="An activity 2",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            access=ActivityAccess.PUBLIC.name,
            language="en"
        )
        self.activity3 = Activity.objects.create(
            id=3,
            name="An activity 3",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            access=ActivityAccess.PUBLIC.name,
            language="en"
        )
        self.activity4 = Activity.objects.create(
            id=4,
            name="An activity 4",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            access=ActivityAccess.PUBLIC.name,
            language="en"
        )

        self.ca1 = CourseActivity.objects.create(
            id=1,
            rank=10,
            course=self.public_course, activity=self.activity1
        )
        self.ca2 = CourseActivity.objects.create(
            id=2,
            rank=20,
            course=self.public_course, activity=self.activity2
        )
        self.ca3 = CourseActivity.objects.create(
            id=3,
            rank=30,
            course=self.public_course, activity=self.activity3
        )
        self.ca4 = CourseActivity.objects.create(
            id=4,
            rank=40,
            course=self.public_course, activity=self.activity4
        )

        # ed is owner on all courses
        for user, role in ((self.ed, CollaboratorRole.OWNER),
                           (self.acd, CollaboratorRole.TEACHER),
                           (self.lt, CollaboratorRole.NON_EDITOR_TEACHER)):
            for course in (
            self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
                CourseCollaborator.objects.create(collaborator=user, course=course, role=role.name)

        self.anon_client = Client()

    def assert_owner_form_in_html(self, content):
        content = content.decode("utf-8")
        self.assertIn("id_name", content)
        self.assertIn("id_registration_enabled", content)
        self.assertIn("id_access", content)
        self.assertIn("id_tags", content)
        self.assertIn("id_description", content)

    def assert_teacher_form_in_html(self, content):
        content = content.decode("utf-8")
        self.assertIn("id_name", content)
        self.assertNotIn("id_registration_enabled", content)
        self.assertNotIn("id_access", content)
        self.assertIn("id_tags", content)
        self.assertIn("id_description", content)

    def test_course_update_view_has_permission_because_author(self):
        for course in (
        self.public_course, self.students_only_course, self.collaborators_only_course, self.private_course):
            response = ClientFactory.get_client_for_user("ws").get(
                reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "learning/course/details/change.html")
            self.assert_owner_form_in_html(response.content)

    def test_course_update_view_has_permission_because_owner(self):
        for course in (self.public_course, self.students_only_course, self.collaborators_only_course):
            response = ClientFactory.get_client_for_user("ed").get(
                reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "learning/course/details/change.html")
            self.assert_owner_form_in_html(response.content)

        response = ClientFactory.get_client_for_user("ed").get(
            reverse("learning:course/update", kwargs={'slug': self.private_course.slug}))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateNotUsed(response, "learning/course/details/change.html")

    def test_course_update_view_has_permission_because_teacher(self):
        for course in (self.public_course, self.students_only_course, self.collaborators_only_course):
            response = ClientFactory.get_client_for_user("acd").get(
                reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "learning/course/details/change.html")
            self.assert_teacher_form_in_html(response.content)

        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:course/update", kwargs={'slug': self.private_course.slug}))
        self.assertEqual(response.status_code, 403)

    def test_course_update_view_no_permission_because_non_editor_teacher(self):
        for course in (
        self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
            response = ClientFactory.get_client_for_user("lt").get(
                reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 403)

    def test_course_update_view_not_logged_in(self):
        for course in (
        self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
            response = self.anon_client.get(reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 302)

    def test_course_update_view_no_permission_unprivileged_user(self):
        get_user_model().objects.create_user(username="gs", password="gs")
        client = Client()
        client.login(username="gs", password="gs")
        for course in (
        self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
            response = client.get(reverse("learning:course/update", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 403)

    def assert_detail_contains_for_author_owner(self, content):
        content = content.decode("utf-8")
        self.assertIn("link-course-detail", content)
        self.assertIn("link-course-add-activity", content)
        self.assertIn("link-course-collaborator", content)
        self.assertIn("link-course-students", content)
        self.assertIn("link-course-similar", content)
        self.assertIn("btn-course-change", content)
        self.assertIn("btn-course-delete", content)

    def test_course_detail_view_permission_public_course_because_author_and_owns_activities(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")
        self.assert_detail_contains_for_author_owner(response.content)

        content = response.content.decode("utf-8")
        for activity in self.public_course.activities:
            self.assertIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_view_as_author(self):
        for course in (
        self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
            for view in ["learning:course/detail", "learning:course/detail/collaborators",
                         "learning:course/detail/students",
                         "learning:course/detail/similar"]:
                response = ClientFactory.get_client_for_user("ws").get(reverse(view, kwargs={'slug': course.slug}))
                self.assertEqual(response.status_code, 200)

    def test_redirection_course_has_no_activities(self):
        Course.objects.create(
            id=99,
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
        )
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activities", kwargs={'slug': 'a-simple-course'}))
        self.assertEqual(response.status_code, 302)

    def test_course_detail_view_as_owner(self):
        for course in (self.public_course, self.students_only_course, self.collaborators_only_course):
            response = ClientFactory.get_client_for_user("ed").get(
                reverse("learning:course/detail", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)

        response = ClientFactory.get_client_for_user("ed").get(
            reverse("learning:course/detail", kwargs={'slug': self.private_course.slug}))
        self.assertEqual(response.status_code, 403)

    def test_course_detail_view_as_teacher(self):
        for course in (self.public_course, self.students_only_course, self.collaborators_only_course):
            response = ClientFactory.get_client_for_user("acd").get(
                reverse("learning:course/detail", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)

        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:course/detail", kwargs={'slug': self.private_course.slug}))
        self.assertEqual(response.status_code, 403)

    def test_course_detail_view_as_student(self):
        user = get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")

        for course in (
        self.public_course, self.private_course, self.students_only_course, self.collaborators_only_course):
            course.students.add(user)
            course.save()

        for course in (self.public_course, self.students_only_course):
            response = client.get(reverse("learning:course/detail", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 200)

        for course in (self.collaborators_only_course, self.private_course):
            response = client.get(reverse("learning:course/detail", kwargs={'slug': course.slug}))
            self.assertEqual(response.status_code, 403)

    def test_course_detail_view_as_anon(self):
        response = self.anon_client.get(reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)

        for course in (self.collaborators_only_course, self.private_course, self.students_only_course):
            response = self.anon_client.get(reverse("learning:course/detail", kwargs={'slug': course.slug}))
            self.assertRedirects(
                response,
                "/admin?next={}".format(reverse("learning:course/detail", kwargs={'slug': course.slug})),
                target_status_code=301
            )  # admin internal redirection to login view

    def test_course_detail_view_permission_public_course_because_owner_and_does_not_own_activities(self):
        response = ClientFactory.get_client_for_user("ed").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")
        self.assert_detail_contains_for_author_owner(response.content)

        content = response.content.decode("utf-8")
        for activity in self.public_course.activities:
            self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_view_permission_public_course_because_teacher_and_does_not_own_activities(self):
        response = ClientFactory.get_client_for_user("acd").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        self.assertIn("link-course-detail", content)
        self.assertIn("link-course-add-activity", content)
        self.assertIn("link-course-collaborator", content)
        self.assertIn("link-course-students", content)
        self.assertIn("link-course-similar", content)
        self.assertIn("btn-course-change", content)
        self.assertNotIn("btn-course-delete", content)

        for activity in self.public_course.activities:
            self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_view_permission_public_course_because_non_editor_teacher_and_does_not_own_activities(self):
        response = ClientFactory.get_client_for_user("lt").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        self.assertIn("link-course-detail", content)
        self.assertNotIn("link-course-add-activity", content)
        self.assertIn("link-course-collaborator", content)
        self.assertIn("link-course-students", content)
        self.assertIn("link-course-similar", content)
        self.assertNotIn("btn-course-change", content)
        self.assertNotIn("btn-course-delete", content)

        for activity in self.public_course.activities:
            self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_view_permission_public_course_because_as_student(self):
        user = get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.students.add(user)
        response = client.get(reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        self.assertIn("link-course-detail", content)
        self.assertIn("link-course-activities", content)
        self.assertNotIn("link-course-add-activity", content)
        self.assertNotIn("link-course-collaborator", content)
        self.assertNotIn("link-course-students", content)
        self.assertIn("link-course-similar", content)
        self.assertNotIn("btn-course-change", content)
        self.assertNotIn("btn-course-delete", content)

        for activity in self.public_course.activities:
            self.assertNotIn("btn-course-activity-{}-view".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_view_permission_public_course_because_as_anon(self):
        response = self.anon_client.get(reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        self.assertIn("link-course-detail", content)
        self.assertIn("link-course-activities", content)
        self.assertNotIn("link-course-add-activity", content)
        self.assertNotIn("link-course-collaborator", content)
        self.assertNotIn("link-course-students", content)
        self.assertNotIn("link-course-similar", content)
        self.assertNotIn("btn-course-change", content)
        self.assertNotIn("btn-course-delete", content)

        for activity in self.public_course.activities:
            self.assertNotIn("btn-course-activity-{}-view".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-unlink".format(activity.id), content)
            self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_collaborators_list(self):
        self.public_course.collaborators.all().delete()
        collaborator = get_user_model().objects.create_user(username="test", first_name="@A_unique_string@",
                                                            last_name="//To test//", password="pwd")
        self.public_course.collaborators.add(collaborator)
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/collaborators", kwargs={'slug': self.public_course.slug}))
        for c in self.public_course.collaborators.all():
            self.assertContains(response, c.username, count=5)
            self.assertContains(response, "@A_unique_string@ //To test//", count=5)

    def test_course_detail_activities_permission_button(self):
        new_activity = Activity.objects.create(name="An activity", description="An activity description",
                                               author=self.lt)
        CourseActivity.objects.create(rank=50, course=self.public_course, activity=new_activity)

        response = ClientFactory.get_client_for_user("lt").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "learning/course/detail.html")

        content = response.content.decode("utf-8")
        for activity in self.public_course.activities:
            if activity == new_activity:
                self.assertIn("btn-course-activity-{}-change".format(activity.id), content)
                self.assertNotIn("btn-course-activity-{}-unlink".format(activity.id), content)
                self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)
            else:
                self.assertNotIn("btn-course-activity-{}-change".format(activity.id), content)
                self.assertNotIn("btn-course-activity-{}-unlink".format(activity.id), content)
                self.assertNotIn("btn-course-activity-{}-delete".format(activity.id), content)

    def test_course_detail_context_data_owner_are_in(self):
        for view in ["learning:course/detail", "learning:course/detail/activities",
                     "learning:course/detail/collaborators", "learning:course/detail/students",
                     "learning:course/detail/similar"]:
            response = ClientFactory.get_client_for_user("ws").get(
                reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertIn("user_can_register", response.context)
            self.assertIn("user_is_teacher", response.context)
            self.assertIn("user_is_student", response.context)
            self.assertNotIn("contribution", response.context)

    def test_course_detail_context_data_collaborator_are_in(self):
        for view in ["learning:course/detail", "learning:course/detail/activities",
                     "learning:course/detail/collaborators", "learning:course/detail/students",
                     "learning:course/detail/similar"]:
            response = ClientFactory.get_client_for_user("ed").get(
                reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertIn("user_can_register", response.context)
            self.assertIn("user_is_teacher", response.context)
            self.assertIn("user_is_student", response.context)
            # ed collaborates on the course
            self.assertIn("contribution", response.context)

    def test_course_detail_context_data_for_anon(self):
        self.public_course.registration_enabled = True
        for view in ["learning:course/detail", "learning:course/detail/activities"]:
            response = self.anon_client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertTrue(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertFalse(response.context.get('user_is_student'))

    def test_course_detail_context_data_for_connected_user_already_student(self):
        user = get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.students.add(user)
        self.public_course.registration_enabled = True
        self.public_course.save()
        for view in ["learning:course/detail", "learning:course/detail/activities",
                     "learning:course/detail/similar"]:
            response = client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertTrue(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertTrue(response.context.get('user_is_student'))

    def test_course_detail_context_data_for_connected_user_not_student(self):
        get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.registration_enabled = True
        self.public_course.save()
        for view in ["learning:course/detail", "learning:course/detail/activities"]:
            response = client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertTrue(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertFalse(response.context.get('user_is_student'))

    def test_course_detail_context_data_for_connected_user_not_student_registration_disabled(self):
        get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.registration_enabled = False
        self.public_course.save()
        for view in ["learning:course/detail", "learning:course/detail/activities"]:
            response = client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertFalse(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertFalse(response.context.get('user_is_student'))

    def test_course_detail_context_data_for_connected_user_not_student_registration_enabled_archived(self):
        get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.registration_enabled = True
        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.save()
        for view in ["learning:course/detail", "learning:course/detail/activities"]:
            response = client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertFalse(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertFalse(response.context.get('user_is_student'))

    def test_course_detail_context_data_for_connected_user_not_student_registration_enabled_draft(self):
        get_user_model().objects.create_user("user", "", "pwd")
        client = Client()
        client.login(username="user", password="pwd")
        self.public_course.registration_enabled = True
        self.public_course.state = CourseState.DRAFT.name
        self.public_course.save()
        for view in ["learning:course/detail", "learning:course/detail/activities"]:
            response = client.get(reverse(view, kwargs={'slug': self.public_course.slug}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed("learning/detail.html")
            self.assertFalse(response.context.get('user_can_register'))
            self.assertFalse(response.context.get('user_is_teacher'))
            self.assertFalse(response.context.get('user_is_student'))

    """
    activity_on_course_up_view
    """

    def test_get_post_course_up_view(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': 1}
        )
        self.assertEqual(405, response.status_code)

    def test_post_up_activity_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_up_activity_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_up_activity_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_post_course_up_view_first_course(self):
        self.public_course.course_activities.all().delete()
        self.public_course.course_activities.create(activity=self.activity1, course=self.public_course, rank=1)
        self.public_course.course_activities.create(activity=self.activity2, course=self.public_course, rank=2)
        self.public_course.course_activities.create(activity=self.activity3, course=self.public_course, rank=3)
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': 1}
        )
        self.assertEqual(404, response.status_code)

    def test_post_course_up_view_last_course(self):
        self.public_course.course_activities.all().delete()
        self.public_course.course_activities.create(activity=self.activity1, course=self.public_course, rank=1)
        self.public_course.course_activities.create(activity=self.activity2, course=self.public_course, rank=2)
        self.public_course.course_activities.create(activity=self.activity3, course=self.public_course, rank=3)
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': 3}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(self.activity3, self.public_course.course_activities.filter(rank=2).get().activity)
        self.assertEqual(self.activity2, self.public_course.course_activities.filter(rank=3).get().activity)

    def test_post_course_up_view(self):
        self.public_course.course_activities.all().delete()
        self.public_course.course_activities.create(activity=self.activity1, course=self.public_course, rank=1)
        self.public_course.course_activities.create(activity=self.activity2, course=self.public_course, rank=2)
        self.public_course.course_activities.create(activity=self.activity3, course=self.public_course, rank=3)
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': 2}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(self.activity2, self.public_course.course_activities.filter(rank=1).get().activity)
        self.assertEqual(self.activity1, self.public_course.course_activities.filter(rank=2).get().activity)

    def test_post_course_up_view_forbidden(self):
        self.assertFalse(self.public_course.user_can_change(self.lt))
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/activity/up", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertEqual(403, response.status_code)

    """
    activity_on_course_unlink_view
    """

    def test_get_unlink_activity(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(405, response.status_code)

    def test_post_unlink_activity_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_unlink_activity_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_unlink_activity_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_get_activity_on_course_unlink_view_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertEqual(405, response.status_code)
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(Activity.objects.filter(id=self.activity1.id).exists())

    def test_post_activity_on_course_unlink_view(self):
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertFalse(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(Activity.objects.filter(id=self.activity1.id).exists())

    def test_post_activity_on_course_unlink_view_forbidden(self):
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertFalse(self.public_course.user_can_change(self.lt))
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/activity/unlink", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertEqual(403, response.status_code)
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(Activity.objects.filter(id=self.activity1.id).exists())

    """
    activity_on_course_delete_view
    """

    def test_get_delete_activity(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(405, response.status_code)

    def test_post_delete_activity_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_activity_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_activity_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_get_activity_on_course_delete_view_not_allowed(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': 1}
        )
        self.assertEqual(405, response.status_code)
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(Activity.objects.filter(id=self.activity1.id).exists())

    def test_post_activity_on_course_delete_view(self):
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertFalse(self.public_course.course_activities.filter(activity=self.activity1).exists())
        with self.assertRaises(ObjectDoesNotExist):
            Activity.objects.get(pk=self.activity1.id)

    def test_post_activity_on_course_delete_view_forbidden(self):
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertFalse(self.public_course.user_can_change(self.lt))
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/activity/delete", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity1.id}
        )
        self.assertEqual(403, response.status_code)
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity1).exists())
        self.assertTrue(Activity.objects.filter(id=self.activity1.id).exists())

    """
    CourseRegisterView
    """

    def test_post_register_view_registration_enabled(self):
        john_doe = get_user_model().objects.create_user(username="john-doe", password="pwd")
        john_doe_client = Client()
        john_doe_client.login(username="john-doe", password="pwd")
        self.assertFalse(self.public_course.students.filter(username=john_doe.username).exists())
        self.assertTrue(self.public_course.can_register)
        response = john_doe_client.post(
            reverse("learning:course/detail/register", kwargs={'slug': self.public_course.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertTrue(self.public_course.students.filter(username=john_doe.username).exists())

    def test_post_register_view_registration_disabled(self):
        john_doe = get_user_model().objects.create_user(username="john-doe", password="pwd")
        john_doe_client = Client()
        john_doe_client.login(username="john-doe", password="pwd")
        self.assertFalse(self.public_course.students.filter(username=john_doe.username).exists())
        self.public_course.registration_enabled = False
        self.public_course.save()
        self.assertFalse(self.public_course.can_register)
        response = john_doe_client.post(
            reverse("learning:course/detail/register", kwargs={'slug': self.public_course.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertFalse(self.public_course.students.filter(username=john_doe.username).exists())

    def test_get_register_view(self):
        john_doe = get_user_model().objects.create_user(username="john-doe", password="pwd")
        john_doe_client = Client()
        john_doe_client.login(username="john-doe", password="pwd")
        self.assertFalse(self.public_course.students.filter(username=john_doe.username).exists())
        response = john_doe_client.get(
            reverse("learning:course/detail/register", kwargs={'slug': self.public_course.slug})
        )
        self.assertFalse(self.public_course.students.filter(username=john_doe.username).exists())
        self.assertEqual(405, response.status_code)

    """
    CourseUnregisterView
    """

    def test_post_unregister_view_registration_enabled(self):
        self.public_course.students.add(self.lt)
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())
        self.assertTrue(self.public_course.can_register)
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/unregister", kwargs={'slug': self.public_course.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertFalse(self.public_course.students.filter(username=self.lt.username).exists())

    def test_post_unregister_view_registration_disabled(self):
        self.public_course.students.add(self.lt)
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())
        self.public_course.registration_enabled = False
        self.public_course.save()
        self.assertFalse(self.public_course.can_register)
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/unregister", kwargs={'slug': self.public_course.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())

    def test_post_unregister_view_registration_enabled_but_registration_locked_for_user(self):
        self.public_course.students.add(self.lt)
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())
        self.public_course.registration_enabled = True
        self.public_course.save()
        self.assertTrue(self.public_course.can_register)
        RegistrationOnCourse.objects.filter(course=self.public_course, student=self.lt).update(registration_locked=True)
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/unregister", kwargs={'slug': self.public_course.slug})
        )
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail", kwargs={'slug': self.public_course.slug})
        )
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())

    def test_get_unregister_view(self):
        self.public_course.students.add(self.lt)
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())
        response = ClientFactory.get_client_for_user("lt").get(
            reverse("learning:course/detail/unregister", kwargs={'slug': self.public_course.slug})
        )
        self.assertTrue(self.public_course.students.filter(username=self.lt.username).exists())
        self.assertEqual(405, response.status_code)

    """
    CourseDetailActivityResourceView
    """

    def test_course_detail_activity_resource_view(self):
        self.public_course.user_can_view(self.lt)

        r1 = Resource.objects.create(name="A sample resource", author=self.ws, language="en")
        self.activity1.resources.add(r1)

        self.assertIn(self.activity1, self.public_course.activities)
        self.assertTrue(self.activity1.resources.filter(id=r1.id).exists())

        response = ClientFactory.get_client_for_user("lt").get(
            reverse(
                "learning:course/detail/activities/resource",
                kwargs={'slug': self.public_course.slug, 'activity_slug': self.activity1.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, "learning/course/details/activity_resource.html")
        self.assertEqual(self.activity1, response.context.get('activity'))
        self.assertEqual(r1, response.context.get('resource'))

    def test_course_detail_activity_resource_view_no_resource(self):
        self.public_course.user_can_view(self.lt)

        r1 = Resource.objects.create(name="A sample resource", author=self.ws)

        self.assertIn(self.activity1, self.public_course.activities)
        self.assertFalse(self.activity1.resources.filter(id=r1.id).exists())

        response = ClientFactory.get_client_for_user("lt").get(
            reverse(
                "learning:course/detail/activities/resource",
                kwargs={'slug': self.public_course.slug, 'activity_slug': self.activity1.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(404, response.status_code)

    def test_course_detail_activity_resource_view_no_activity(self):
        self.public_course.user_can_view(self.lt)

        self.public_course.course_activities.filter(activity=self.activity1).delete()
        r1 = Resource.objects.create(name="A sample resource", author=self.ws)
        self.activity1.resources.add(r1)

        self.assertNotIn(self.activity1, self.public_course.activities)
        self.assertTrue(self.activity1.resources.filter(id=r1.id).exists())

        response = ClientFactory.get_client_for_user("lt").get(
            reverse(
                "learning:course/detail/activities/resource",
                kwargs={'slug': self.public_course.slug, 'activity_slug': self.activity1.slug, 'resource_slug': r1.slug}
            )
        )
        self.assertEqual(404, response.status_code)

    """
    CourseDetailCollaboratorsAddView
    """

    def test_post_add_course_collaborator_as_teacher_forbidden(self):
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).delete()
        self.assertNotIn("add_collaborator_course", self.public_course.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/collaborator/add", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.acd.id, 'role': CollaboratorRole.NON_EDITOR_TEACHER.name}
        )
        self.assertEqual(403, response.status_code)
        self.assertNotIn(self.acd, self.public_course.collaborators.all())

    def test_post_add_course_collaborator_as_non_editor_teacher(self):
        self.assertEqual(self.ws, self.public_course.author)
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).delete()
        self.assertEqual(2, self.public_course.collaborators.count())
        self.assertIn("add_collaborator_course", self.public_course.get_user_perms(self.ws))
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/add", kwargs={'slug': self.public_course.slug}),
            {'username': self.acd.username, 'roles': CollaboratorRole.NON_EDITOR_TEACHER.name}
        )
        self.assertRedirects(
            response, target_status_code=200,
            expected_url=reverse("learning:course/detail/collaborators", kwargs={'slug': self.public_course.slug})
        )
        self.assertIn(self.acd, self.public_course.collaborators.all())
        self.assertEqual(3, self.public_course.collaborators.count())

    """
    CourseDetailCollaboratorsChangeView
    """

    def test_get_change_collaborator(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
        )
        self.assertEqual(405, response.status_code)

    def test_post_change_collaborator_user_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
            {'user_pk': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_change_collaborator_user_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
            {'user_pk': 0}
        )
        self.assertEqual(404, response.status_code)

    def test_post_change_collaborator_user_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_post_change_collaborator_role_as_teacher_forbidden(self):
        CourseCollaborator.objects.filter(collaborator=self.lt, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        self.assertNotIn("change_collaborator_course", self.public_course.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.lt.id, 'role': CollaboratorRole.NON_EDITOR_TEACHER.name}
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(CollaboratorRole.TEACHER.name,
                         CourseCollaborator.objects.get(course=self.public_course, collaborator=self.lt).role)

    def test_post_change_collaborator_role_as_owner_teacher_to_non_editor_teacher(self):
        self.assertEquals(self.public_course.author, self.ws)
        self.assertIn("change_collaborator_course", self.public_course.get_user_perms(self.ws))
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.acd.id, 'role': CollaboratorRole.NON_EDITOR_TEACHER.name}
        )
        self.assertRedirects(
            response,
            expected_url=reverse("learning:course/detail/collaborators", kwargs={'slug': self.public_course.slug})
        )
        self.assertIn(self.acd, self.public_course.collaborators.all())
        self.assertEqual(CollaboratorRole.NON_EDITOR_TEACHER.name,
                         CourseCollaborator.objects.get(course=self.public_course, collaborator=self.acd).role)

    def test_post_change_collaborator_role_as_owner_teacher_to_teacher(self):
        self.assertEquals(self.public_course.author, self.ws)
        self.assertIn("change_collaborator_course", self.public_course.get_user_perms(self.ws))
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        self.assertIn(self.acd, self.public_course.collaborators.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/change", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.acd.id, 'role': CollaboratorRole.TEACHER.name}
        )
        self.assertRedirects(
            response,
            expected_url=reverse("learning:course/detail/collaborators", kwargs={'slug': self.public_course.slug})
        )
        self.assertIn(self.acd, self.public_course.collaborators.all())
        self.assertEqual(CollaboratorRole.TEACHER.name,
                         CourseCollaborator.objects.get(course=self.public_course, collaborator=self.acd).role)

    """
    CourseDetailCollaboratorsDeleteView
    """

    def test_get_delete_collaborator(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug}),
        )
        self.assertEqual(405, response.status_code)

    def test_post_delete_collaborator_user_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_collaborator_user_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': 0}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_collaborator_user_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_collaborator_from_a_course_forbidden(self):
        CourseCollaborator.objects.filter(collaborator=self.lt, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).update(
            role=CollaboratorRole.TEACHER.name)
        self.assertNotIn("delete_collaborator_course", self.public_course.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.lt.id}
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual(CollaboratorRole.TEACHER.name,
                         CourseCollaborator.objects.get(course=self.public_course, collaborator=self.lt).role)

    def test_post_delete_collaborator_from_a_course(self):
        self.assertEquals(self.public_course.author, self.ws)
        self.assertIn("delete_collaborator_course", self.public_course.get_user_perms(self.ws))
        self.assertIn(self.acd, self.public_course.collaborators.all())
        self.assertEqual(3, self.public_course.collaborators.count())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/collaborator/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.acd.id}
        )
        self.assertRedirects(
            response,
            expected_url=reverse("learning:course/detail/collaborators", kwargs={'slug': self.public_course.slug})
        )
        self.assertNotIn(self.acd, self.public_course.collaborators.all())
        self.assertEqual(2, self.public_course.collaborators.count())

    """
    CourseDetailStudentsAddView
    """

    def test_post_add_student_on_course_as_non_editor_teacher_forbidden(self):
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).delete()
        self.assertNotIn("add_collaborator_course", self.public_course.get_user_perms(self.acd))
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/students/add", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.acd.id, 'locked': True}
        )
        self.assertEqual(403, response.status_code)
        self.assertNotIn(self.acd, self.public_course.collaborators.all())

    def test_post_add_student_on_course_registration_locked(self):
        CourseCollaborator.objects.filter(course=self.public_course, collaborator=self.acd).delete()
        self.assertIn("add_collaborator_course", self.public_course.get_user_perms(self.ws))
        self.assertNotIn(self.acd, self.public_course.students.all())
        self.assertNotIn(self.acd, self.public_course.collaborators.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/add", kwargs={'slug': self.public_course.slug}),
            {'username': self.acd.username, 'registration_locked': True}
        )
        self.assertRedirects(
            response, target_status_code=200,
            expected_url=reverse("learning:course/detail/students", kwargs={'slug': self.public_course.slug})
        )
        self.assertIn(self.acd, self.public_course.students.all())
        self.assertTrue(
            RegistrationOnCourse.objects.filter(student=self.acd, course=self.public_course).get().registration_locked)

    def test_post_add_student_on_course_registration_not_locked(self):
        CourseCollaborator.objects.filter(course=self.public_course, collaborator=self.acd).delete()
        self.assertIn("add_collaborator_course", self.public_course.get_user_perms(self.ws))
        self.assertNotIn(self.acd, self.public_course.students.all())
        self.assertNotIn(self.acd, self.public_course.collaborators.all())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/add", kwargs={'slug': self.public_course.slug}),
            {'username': self.acd.username, 'registration_locked': False}
        )
        self.assertRedirects(
            response, target_status_code=200,
            expected_url=reverse("learning:course/detail/students", kwargs={'slug': self.public_course.slug})
        )
        self.assertIn(self.acd, self.public_course.students.all())
        self.assertFalse(
            RegistrationOnCourse.objects.filter(student=self.acd, course=self.public_course).get().registration_locked)

    """
    CourseDetailStudentsChangeView
    """

    def test_get_delete_student(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/students/change", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(405, response.status_code)

    def test_post_change_student_registration_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/change", kwargs={'slug': self.public_course.slug,
                                                                      'registration_pk': 0}),
        )
        self.assertEqual(404, response.status_code)

    """
    CourseDetailStudentsDeleteView
    """

    def test_get_delete_student(self):
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug}),
        )
        self.assertEqual(405, response.status_code)

    def test_post_delete_student_registration_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_student_registration_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': 0}
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_student_registration_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_post_delete_student_from_a_course_forbidden_as_non_editor_teacher(self):
        CourseCollaborator.objects.filter(collaborator=self.lt, course=self.public_course).delete()
        CourseCollaborator.objects.filter(collaborator=self.acd, course=self.public_course).update(
            role=CollaboratorRole.NON_EDITOR_TEACHER.name
        )
        self.assertNotIn("delete_student_course", self.public_course.get_user_perms(self.acd))
        RegistrationOnCourse.objects.create(course=self.public_course, student=self.lt)
        self.assertIn(self.lt, self.public_course.students.all())
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.lt.id}
        )
        self.assertEqual(403, response.status_code)
        self.assertIn(self.lt, self.public_course.students.all())

    def test_post_delete_student_from_a_course(self):
        CourseCollaborator.objects.filter(collaborator=self.lt, course=self.public_course).delete()
        self.assertIn("delete_student_course", self.public_course.get_user_perms(self.ws))
        RegistrationOnCourse.objects.create(course=self.public_course, student=self.lt)
        self.assertIn(self.lt, self.public_course.students.all())
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug}),
            {'user_pk': self.lt.id}
        )
        self.assertRedirects(
            response, target_status_code=200,
            expected_url=reverse("learning:course/detail/students", kwargs={'slug': self.public_course.slug})
        )
        self.assertNotIn(self.lt, self.public_course.students.all())

    def test_post_delete_student_from_a_course_invalid_input_str(self):
        response = ClientFactory.get_client_for_user("acd").post(
            reverse("learning:course/detail/students/delete", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    """
    ActivityCreateOnCourseView
    """

    def test_get_activity_create_on_course_view_forbidden(self):
        self.assertTrue(self.public_course.user_can_change(self.ws))
        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/add", kwargs={'slug': self.public_course.slug}), {}
        )
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "id_name", count=2)
        self.assertContains(response, "id_language", count=2)
        self.assertContains(response, "id_access", count=2)
        self.assertContains(response, "id_reuse", count=2)
        self.assertContains(response, "id_tags", count=2)
        self.assertContains(response, "id_description", count=2)

    def test_post_activity_create_on_course_view_forbidden(self):
        self.assertFalse(self.public_course.user_can_change(self.lt))
        response = ClientFactory.get_client_for_user("lt").post(
            reverse("learning:course/detail/activity/add", kwargs={'slug': self.public_course.slug}), {}
        )
        self.assertEqual(403, response.status_code)

    def test_post_activity_create_on_course_view(self):
        self.public_course.course_activities.all().delete()
        self.public_course.user_can_change(self.ws)
        self.assertEqual(0, self.public_course.course_activities.count())
        form_data = {
            'name': "A sample name",
            'description': "A short description",
            'language': 'fr',
            'reuse': ActivityReuse.NO_RESTRICTION.name,
            'access': ActivityAccess.PUBLIC.name,
            'tags': "A"
        }
        self.assertFalse(Activity.objects.filter(name="A sample name").exists())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/add", kwargs={'slug': self.public_course.slug}), form_data
        )
        self.assertTrue(Activity.objects.filter(name="A sample name").exists())
        activity = Activity.objects.filter(name="A sample name").get()
        self.assertRedirects(
            response, target_status_code=200, status_code=302,
            expected_url=reverse("learning:activity/detail",
                                 kwargs={'slug': activity.slug})
        )
        self.assertIn(activity, self.public_course.activities)
        self.assertEqual(1, self.public_course.course_activities.count())

    def test_post_activity_create_on_course_view_exception_activity_not_reusable(self):
        self.public_course.course_activities.all().delete()
        self.public_course.user_can_change(self.ws)
        self.assertEqual(0, self.public_course.course_activities.count())
        form_data = {
            'name': "A sample name",
            'description': "A short description",
            'language': 'fr',
            'reuse': ActivityReuse.NON_REUSABLE.name,
            'access': ActivityAccess.PUBLIC.name,
            'tags': "A"
        }
        self.assertFalse(Activity.objects.filter(name="A sample name").exists())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/add", kwargs={'slug': self.public_course.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(Activity.objects.filter(name="A sample name").exists())
        self.assertEqual(0, self.public_course.course_activities.count())
        for value in form_data.values():
            self.assertContains(response, value)

    def test_post_activity_create_on_course_view_invalid_form(self):
        self.public_course.course_activities.all().delete()
        self.public_course.user_can_change(self.ws)
        self.assertEqual(0, self.public_course.course_activities.count())
        form_data = {
            'description': "A short description",
            'language': 'fr',
            'reuse': ActivityReuse.NO_RESTRICTION.name,
            'access': ActivityAccess.PUBLIC.name,
            'tags': "A"
        }
        self.assertFalse(Activity.objects.filter(name="A sample name").exists())
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/add", kwargs={'slug': self.public_course.slug}), form_data
        )
        self.assertEqual(200, response.status_code)
        self.assertFalse(Activity.objects.filter(name="A sample name").exists())
        self.assertEqual(0, self.public_course.course_activities.count())
        self.assertEqual(1, len(response.context.get('form').errors.as_data()))
        for value in form_data.values():
            self.assertContains(response, value)

    """
    ActivityAttachOnCourseView
    """

    def test_post_attach_activity_pk_as_string(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_attach_activity_pk_below_one(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug}),
            {'activity': "Test"}
        )
        self.assertEqual(404, response.status_code)

    def test_post_attach_activity_pk_not_found(self):
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(404, response.status_code)

    def test_get_activity_attach_on_course_view(self):
        self.assertTrue(self.public_course.user_can_change(self.ws))
        self.public_course.course_activities.all().delete()

        self.public_course.add_activity(self.activity1)

        self.activity2.reuse = ActivityReuse.NON_REUSABLE.name
        self.activity2.save()

        self.activity3.reuse = ActivityReuse.ONLY_AUTHOR.name
        self.activity3.author = self.public_course.author
        self.activity3.save()

        self.activity4.reuse = ActivityReuse.ONLY_AUTHOR.name
        self.activity4.author = self.lt
        self.activity4.save()

        a5 = Activity.objects.create(id=5, name="activity5", reuse=ActivityReuse.NO_RESTRICTION, author=self.acd, language="en")
        a6 = Activity.objects.create(id=6, name="activity6", reuse=ActivityReuse.NO_RESTRICTION, author=self.lt, language="en")
        a7 = Activity.objects.create(id=7, name="activity7", reuse=ActivityReuse.NO_RESTRICTION, author=self.acd, language="en")
        a8 = Activity.objects.create(id=8, name="activity8", reuse=ActivityReuse.NO_RESTRICTION, author=self.lt, language="en")

        response = ClientFactory.get_client_for_user("ws").get(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug})
        )

        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed("learning/course/details/attach_activity.html")
        self.assertIsInstance(response.context.get('form'), BasicSearchForm)
        self.assertIsNotNone(response.context.get('reusable_page_obj'))

        reusable_objects = response.context.get('reusable_page_obj').object_list
        self.assertNotIn(self.activity1, reusable_objects)
        self.assertNotIn(self.activity2, reusable_objects)
        self.assertIn(self.activity3, reusable_objects)
        self.assertNotIn(self.activity4, reusable_objects)
        self.assertIn(a5, reusable_objects)
        self.assertIn(a6, reusable_objects)
        self.assertIn(a7, reusable_objects)
        self.assertIn(a8, reusable_objects)

    def test_get_activity_attach_on_course_view_forbidden(self):
        self.assertFalse(self.public_course.user_can_change(self.lt))
        self.public_course.course_activities.all().delete()
        response = ClientFactory.get_client_for_user("lt").get(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug})
        )
        self.assertEqual(403, response.status_code)

    def test_post_activity_attach_on_course_view(self):
        self.assertTrue(self.public_course.user_can_change(self.ws))
        self.public_course.course_activities.all().delete()
        response = ClientFactory.get_client_for_user("ws").post(
            reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug}),
            {'activity': self.activity2.id}
        )
        self.assertRedirects(
            response, status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail/activity/attach", kwargs={'slug': self.public_course.slug})
        )
        self.assertTrue(self.public_course.course_activities.filter(activity=self.activity2).exists())
