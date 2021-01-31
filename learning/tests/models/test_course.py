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
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase

from learning.exc import RegistrationDisabledError, UserIsAlreadyCollaborator, \
    UserIsAlreadyAuthor, UserNotCollaboratorError, UserIsNotStudent, UserIsAlreadyStudent, ChangeActivityOnCourseError, \
    ActivityAlreadyOnCourseError, ActivityNotReusableError, \
    ActivityIsNotLinkedWithThisCourseError
from learning.models import Course, CollaboratorRole, CourseAccess, CourseState, CourseCollaborator, Activity, \
    CourseActivity, ActivityReuse, RegistrationOnCourse


class CourseTestCase(TestCase):
    def setUp(self) -> None:
        get_user_model().objects.create_user(id=1, username="william-shakespeare")
        get_user_model().objects.create_user(id=2, username="emily-dickinson")
        get_user_model().objects.create_user(id=3, username="h-p-lovecraft")
        get_user_model().objects.create_user(id=4, username="arthur-conan-doyle")
        get_user_model().objects.create_user(id=5, username="leo-tolstoy")

        self.private_course = Course.objects.create(
            id=1,
            name="A simple private course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PRIVATE.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.public_course = Course.objects.create(
            id=2,
            name="A simple public course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PUBLIC.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True,
            language="en"
        )

        self.students_only_course = Course.objects.create(
            id=3,
            name="A simple students only course",
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
            name="A simple collaborators only course",
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
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            language="en"
        )
        self.activity2 = Activity.objects.create(
            id=2,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            language="en"
        )
        self.activity3 = Activity.objects.create(
            id=3,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            language="en"
        )
        self.activity4 = Activity.objects.create(
            id=4,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
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


class CourseUserPermsTest(CourseTestCase):

    def test_no_perm_for_collaborators_on_private_course(self):
        user = get_user_model().objects.get(pk=2)
        CourseCollaborator.objects.create(course=self.private_course, collaborator=user,
                                          role=CollaboratorRole.OWNER.name)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(sorted([]), sorted(self.private_course.get_user_perms(user)))

        user = get_user_model().objects.get(pk=3)
        CourseCollaborator.objects.create(course=self.private_course, collaborator=user,
                                          role=CollaboratorRole.NON_EDITOR_TEACHER.name)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(sorted([]), sorted(self.private_course.get_user_perms(user)))

        user = get_user_model().objects.get(pk=4)
        CourseCollaborator.objects.create(course=self.private_course, collaborator=user,
                                          role=CollaboratorRole.TEACHER.name)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(sorted([]), sorted(self.private_course.get_user_perms(user)))

    def test_no_perm_for_student_on_private_course(self):
        user = get_user_model().objects.get(pk=4)
        self.private_course.students.add(user)
        self.assertIn(user, self.private_course.students.all())
        self.assertEqual(sorted(self.private_course.get_user_perms(user)), [])

    def test_perms_for_collaborator_as_owner_on_public_course(self):
        user = get_user_model().objects.get(pk=2)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.OWNER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'add_objective_course', 'delete_objective_course', 'view_objective_course','change_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_author_on_public_course(self):
        user = get_user_model().objects.get(pk=1)
        self.assertEqual(user, self.public_course.author)
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'add_objective_course', 'delete_objective_course', 'change_objective_course', 'view_objective_course',

        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_author_on_private_course(self):
        user = get_user_model().objects.get(pk=1)
        self.assertEqual(user, self.public_course.author)
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'add_objective_course', 'delete_objective_course', 'view_objective_course', 'change_objective_course',

        ]
        self.assertEqual(sorted(self.private_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_author_on_students_only_course(self):
        user = get_user_model().objects.get(pk=1)
        self.assertEqual(user, self.public_course.author)
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'add_objective_course', 'delete_objective_course', 'change_objective_course', 'view_objective_course',
        ]
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_author_on_collaborators_only_course(self):
        user = get_user_model().objects.get(pk=1)
        self.assertEqual(user, self.public_course.author)
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'add_objective_course', 'change_objective_course', 'delete_objective_course', 'view_objective_course'
            ,
        ]
        self.assertEqual(sorted(self.collaborators_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_non_editor_teacher_on_public_course(self):
        user = get_user_model().objects.get(pk=3)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.NON_EDITOR_TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course",
            "view_collaborators_course", "view_students_course", 'view_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_teacher_on_public_course(self):
        user = get_user_model().objects.get(pk=4)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course",
            "view_collaborators_course", "view_students_course",
            "add_student_course", "change_student_course", "delete_student_course",
            'add_objective_course', 'delete_objective_course', 'view_objective_course','change_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_owner_on_students_only_course(self):
        user = get_user_model().objects.get(pk=2)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.OWNER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course",
            "delete_collaborator_course", "delete_student_course",
            'change_collaborator_course', "change_student_course",
            'view_objective_course', 'add_objective_course', 'delete_objective_course','change_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_non_editor_teacher_on_students_only_course(self):
        user = get_user_model().objects.get(pk=3)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.NON_EDITOR_TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course",
            "view_collaborators_course", "view_students_course", 'view_objective_course',

        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_teacher_on_students_only_course(self):
        user = get_user_model().objects.get(pk=4)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course",
            "view_collaborators_course", "view_students_course",
            "add_student_course", "change_student_course", "delete_student_course",
            'add_objective_course', 'delete_objective_course', 'view_objective_course','change_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_owner_on_collaborators_only_course(self):
        user = get_user_model().objects.get(pk=2)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.OWNER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course", "delete_course",
            "view_collaborators_course", "view_students_course", "change_privacy_course",
            "add_collaborator_course", "add_student_course", "delete_student_course", "delete_collaborator_course",
            'change_collaborator_course', "change_student_course", 'add_objective_course',
            'delete_objective_course', 'view_objective_course', 'change_objective_course',

        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_non_editor_teacher_on_collaborators_only_course(self):
        user = get_user_model().objects.get(pk=3)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.NON_EDITOR_TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course",
            "view_collaborators_course", "view_students_course", 'view_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_collaborator_as_teacher_on_collaborators_only_course(self):
        user = get_user_model().objects.get(pk=4)
        CourseCollaborator.objects.create(course=self.public_course, collaborator=user,
                                          role=CollaboratorRole.TEACHER.name)
        self.assertIn(user, self.public_course.collaborators.all())
        expected_perms = [
            "view_course", "view_hidden_course", "view_similar_course", "add_course", "change_course",
            "view_collaborators_course", "view_students_course",
            "add_student_course", "change_student_course", "delete_student_course",
            'add_objective_course', 'delete_objective_course', 'view_objective_course','change_objective_course',
        ]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_student_on_public_course(self):
        user = get_user_model().objects.get(pk=4)
        expected_perms = ["view_course"]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))
        self.public_course.students.add(user)
        expected_perms = ["view_course", "view_similar_course"]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_student_on_students_only_course(self):
        user = get_user_model().objects.get(pk=4)
        expected_perms = []
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))
        self.students_only_course.students.add(user)
        expected_perms = ["view_course", "view_similar_course"]
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_student_on_collaborators_only_course(self):
        user = get_user_model().objects.get(pk=4)
        expected_perms = []
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))
        self.collaborators_only_course.students.add(user)
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_student_on_private_course(self):
        user = get_user_model().objects.get(pk=4)
        expected_perms = []
        self.assertEqual(sorted(self.private_course.get_user_perms(user)), sorted(expected_perms))
        self.private_course.students.add(user)
        self.assertEqual(sorted(self.private_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_anonymous_on_public_course(self):
        user = AnonymousUser()
        expected_perms = ["view_course"]
        self.assertEqual(sorted(self.public_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_anonymous_on_students_only_course(self):
        user = AnonymousUser()
        expected_perms = []
        self.assertEqual(sorted(self.students_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_anonymous_on_collaborators_only_course(self):
        user = AnonymousUser()
        expected_perms = []
        self.assertEqual(sorted(self.collaborators_only_course.get_user_perms(user)), sorted(expected_perms))

    def test_perms_for_anonymous_on_private_course(self):
        user = AnonymousUser()
        expected_perms = []
        self.assertEqual(sorted(self.collaborators_only_course.get_user_perms(user)), sorted(expected_perms))


class CourseTest(CourseTestCase):
    """
    Default values
    """

    def test_default_values_for_attributes(self):
        course = Course.objects.create(author=get_user_model().objects.get(pk=1),
                                       name="A sample name to test the /slug generator")
        self.assertEqual(course.state, CourseState.DRAFT.name)
        self.assertEqual(course.access, CourseAccess.PUBLIC.name)
        self.assertEqual(course.slug, "a-sample-name-to-test-the-slug-generator")

    """
    Property object_collaborators
    """

    def test_object_collaborators(self):
        CourseCollaborator.objects.create(
            collaborator=get_user_model().objects.get(pk=1), role=CollaboratorRole.TEACHER.name,
            course=self.public_course
        )
        self.assertEqual(1, self.public_course.object_collaborators.count())
        self.assertEqual(get_user_model().objects.get(pk=1),
                         self.public_course.object_collaborators.first().collaborator)
        self.assertEqual(CollaboratorRole.TEACHER.name, self.public_course.object_collaborators.first().role)
        self.assertEqual(self.public_course, self.public_course.object_collaborators.first().course)

    """
    Method: can_register
    """

    def test_can_register_on_public_course(self):
        # Draft, with registration enabled
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)
        self.public_course.state = CourseState.DRAFT.name
        self.assertFalse(self.public_course.can_register)
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        # Archived, with registration enabled
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)
        self.public_course.state = CourseState.ARCHIVED.name
        self.assertFalse(self.public_course.can_register)
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        # Published, with registration enabled
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)
        self.public_course.state = CourseState.PUBLISHED.name
        self.assertFalse(self.public_course.can_register)
        self.public_course.registration_enabled = True
        self.assertTrue(self.public_course.can_register)

    def test_can_register_on_collaborators_only_course(self):
        # Draft, with registration enabled
        self.collaborators_only_course.registration_enabled = False
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.state = CourseState.DRAFT.name
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.registration_enabled = True
        self.assertFalse(self.collaborators_only_course.can_register)

        # Archived, with registration enabled
        self.collaborators_only_course.registration_enabled = False
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.state = CourseState.ARCHIVED.name
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.registration_enabled = True
        self.assertFalse(self.collaborators_only_course.can_register)

        # Private, with registration enabled
        self.collaborators_only_course.registration_enabled = False
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.state = CourseState.PUBLISHED.name
        self.assertFalse(self.collaborators_only_course.can_register)
        self.collaborators_only_course.registration_enabled = True
        self.assertTrue(self.collaborators_only_course.can_register)

    def test_can_register_on_students_only_course(self):
        # Draft, with registration enabled
        self.students_only_course.registration_enabled = False
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.state = CourseState.DRAFT.name
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.registration_enabled = True
        self.assertFalse(self.students_only_course.can_register)

        # Archived, with registration enabled
        self.students_only_course.registration_enabled = False
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.state = CourseState.ARCHIVED.name
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.registration_enabled = True
        self.assertFalse(self.students_only_course.can_register)

        # Private, with registration enabled
        self.students_only_course.registration_enabled = False
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.state = CourseState.PUBLISHED.name
        self.assertFalse(self.students_only_course.can_register)
        self.students_only_course.registration_enabled = True
        self.assertTrue(self.students_only_course.can_register)

    def test_can_register_on_private_course(self):
        # Draft, with registration enabled
        self.private_course.registration_enabled = False
        self.assertFalse(self.private_course.can_register)
        self.private_course.state = CourseState.DRAFT.name
        self.assertFalse(self.private_course.can_register)
        self.private_course.registration_enabled = True
        self.assertFalse(self.private_course.can_register)

        # Archived, with registration enabled
        self.private_course.registration_enabled = False
        self.assertFalse(self.private_course.can_register)
        self.private_course.state = CourseState.ARCHIVED.name
        self.assertFalse(self.private_course.can_register)
        self.private_course.registration_enabled = True
        self.assertFalse(self.private_course.can_register)

        # Published, with registration enabled
        self.private_course.registration_enabled = False
        self.assertFalse(self.private_course.can_register)
        self.private_course.state = CourseState.PUBLISHED.name
        self.assertFalse(self.private_course.can_register)
        self.private_course.registration_enabled = True
        self.assertTrue(self.private_course.can_register)

    """
    Method register
    """

    def test_student_cannot_register_because_is_already_student(self):
        user = get_user_model().objects.get(pk=2)

        # Add the user in students
        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyStudent):
            self.public_course.register(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_student_cannot_register_because_is_already_author(self):
        user = get_user_model().objects.get(pk=1)

        # Set the user as the author of the course
        self.public_course.author = user

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyAuthor):
            self.public_course.register(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_register_because_is_already_a_collaborator(self):
        user = get_user_model().objects.get(pk=2)

        # Add the user in the collaborators of the course
        self.public_course.course_collaborators.add(
            CourseCollaborator.objects.create(
                collaborator=user, course=self.public_course, role=CollaboratorRole.TEACHER
            )
        )

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyCollaborator):
            self.public_course.register(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_register_because_registration_is_disabled(self):
        user = get_user_model().objects.get(pk=2)

        # Set registration as disabled but published
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)

        # Test student self-registration
        with self.assertRaises(RegistrationDisabledError):
            self.public_course.register(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_register_because_course_is_a_draft(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.DRAFT.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        with self.assertRaises(RegistrationDisabledError):
            self.public_course.register(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_register_because_course_is_archived(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.state = CourseState.ARCHIVED.name
        with self.assertRaises(RegistrationDisabledError):
            self.public_course.register(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_can_register_on_course(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.register(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        user = get_user_model().objects.get(pk=3)
        self.public_course.register(user)
        self.assertTrue(self.public_course.registrations.get(student=user).self_registration)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(2, self.public_course.students.count())

    """
    Method register_student
    """

    def test_cannot_register_because_is_already_student(self):
        user = get_user_model().objects.get(pk=2)

        # Add the user in students
        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyStudent):
            self.public_course.register_student(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_cannot_register_because_is_already_author(self):
        user = get_user_model().objects.get(pk=1)

        # Set the user as the author of the course
        self.public_course.author = user

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyAuthor):
            self.public_course.register_student(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_cannot_register_because_is_already_a_collaborator(self):
        user = get_user_model().objects.get(pk=2)

        # Add the user in the collaborators of the course
        self.public_course.course_collaborators.add(
            CourseCollaborator.objects.create(
                collaborator=user, course=self.public_course, role=CollaboratorRole.TEACHER
            )
        )

        # Test student self-registration
        with self.assertRaises(UserIsAlreadyCollaborator):
            self.public_course.register_student(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_can_register_even_if_registration_is_disabled(self):
        user = get_user_model().objects.get(pk=2)

        # Set registration as disabled but published
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)

        # Test student registration
        self.public_course.register_student(user)
        self.assertFalse(self.public_course.registrations.get(student=user).self_registration)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_can_register_even_if_registration_is_a_draft(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.DRAFT.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.register_student(user)
        self.assertFalse(self.public_course.registrations.get(student=user).self_registration)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_can_register_even_if_registration_is_archived(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.register_student(user)
        self.assertFalse(self.public_course.registrations.get(student=user).self_registration)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_can_register_on_course(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.register_student(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        user = get_user_model().objects.get(pk=3)
        self.public_course.register_student(user)
        self.assertFalse(self.public_course.registrations.get(student=user).self_registration)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(2, self.public_course.students.count())

    """
    Method unsubscribe
    """

    def test_student_cannot_unsubscribe_because_registration_is_disabled(self):
        user = get_user_model().objects.get(pk=2)

        # Set registration as disabled but published
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        # Test student self-registration
        with self.assertRaises(RegistrationDisabledError):
            self.public_course.unsubscribe(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_student_cannot_unsubscribe_because_course_is_a_draft(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.DRAFT.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        with self.assertRaises(RegistrationDisabledError):
            self.public_course.unsubscribe(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_student_cannot_unsubscribe_because_course_is_archived(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        self.public_course.state = CourseState.ARCHIVED.name
        with self.assertRaises(RegistrationDisabledError):
            self.public_course.unsubscribe(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

    def test_student_cannot_unsubscribe_because_not_a_student(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.public_course.students.all())

        with self.assertRaises(UserIsNotStudent):
            self.public_course.unsubscribe(user)

        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_can_unsubscribe(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.public_course.students.all())
        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())

        self.public_course.unsubscribe(user)
        self.assertNotIn(user, self.public_course.students.all())

    """
    Method unsubscribe student
    """

    def test_student_cannot_unsubscribe_because_registration_even_if_is_disabled(self):
        user = get_user_model().objects.get(pk=2)

        # Set registration as disabled but published
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.registration_enabled = False
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        self.public_course.unsubscribe_student(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_unsubscribe_because_course_even_if_is_a_draft(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.DRAFT.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        self.public_course.unsubscribe_student(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_student_cannot_unsubscribe_because_course_even_if_is_archived(self):
        user = get_user_model().objects.get(pk=2)

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.registration_enabled = True
        self.assertFalse(self.public_course.can_register)

        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())
        self.assertEqual(1, self.public_course.students.count())

        self.public_course.state = CourseState.ARCHIVED.name
        self.public_course.unsubscribe_student(user)
        self.assertNotIn(user, self.public_course.students.all())
        self.assertEqual(0, self.public_course.students.count())

    def test_cannot_unsubscribe_because_not_a_student(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.public_course.students.all())
        with self.assertRaises(UserIsNotStudent):
            self.public_course.unsubscribe_student(user)
        self.assertNotIn(user, self.public_course.students.all())

    def test_can_unsubscribe(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.public_course.students.all())
        self.public_course.students.add(user)
        self.assertIn(user, self.public_course.students.all())

        self.public_course.unsubscribe_student(user)
        self.assertNotIn(user, self.public_course.students.all())

    """
    Method add_collaborator
    """

    def test_cannot_add_collaborator_because_is_already_author(self):
        user = self.private_course.author
        with self.assertRaises(UserIsAlreadyAuthor):
            self.private_course.add_collaborator(user, CollaboratorRole.OWNER)
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(0, self.private_course.collaborators.count())

    def test_cannot_add_collaborator_if_already_collaborator(self):
        user = get_user_model().objects.get(pk=2)
        ca = CourseCollaborator.objects.create(collaborator=user, course=self.public_course,
                                               role=CollaboratorRole.TEACHER.name)
        self.private_course.course_collaborators.add(ca)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())

        with self.assertRaises(UserIsAlreadyCollaborator):
            self.private_course.add_collaborator(user, CollaboratorRole.OWNER)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())

    def test_cannot_add_collaborator_if_already_student(self):
        user = get_user_model().objects.get(pk=2)
        cr = RegistrationOnCourse.objects.create(course=self.private_course, student=user)
        self.private_course.registrations.add(cr)
        self.assertIn(user, self.private_course.students.all())
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.students.count())
        self.assertEqual(0, self.private_course.collaborators.count())

        with self.assertRaises(UserIsAlreadyStudent):
            self.private_course.add_collaborator(user, CollaboratorRole.OWNER)

        self.assertIn(user, self.private_course.students.all())
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.students.count())
        self.assertEqual(0, self.private_course.collaborators.count())

    def test_can_add_collaborator(self):
        user = get_user_model().objects.get(pk=2)
        self.private_course.add_collaborator(user, CollaboratorRole.TEACHER)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())

    """
    Method change_collaborator_role
    """

    def test_cannot_change_collaborator_role_because_is_not_already_one(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(0, self.private_course.collaborators.count())
        with self.assertRaises(UserNotCollaboratorError):
            self.private_course.change_collaborator_role(user, CollaboratorRole.NON_EDITOR_TEACHER)
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(0, self.private_course.collaborators.count())

    def test_change_collaborator_role(self):
        user = get_user_model().objects.get(pk=3)
        ca = CourseCollaborator.objects.create(collaborator=user, course=self.public_course,
                                               role=CollaboratorRole.TEACHER.name)
        self.private_course.course_collaborators.add(ca)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())
        for c in self.private_course.course_collaborators.all():
            if c.collaborator == user:
                self.assertEqual(CollaboratorRole.TEACHER.name, c.role)
        self.private_course.change_collaborator_role(user, CollaboratorRole.OWNER)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())
        for c in self.private_course.course_collaborators.all():
            if c.collaborator == user:
                self.assertEqual(CollaboratorRole.OWNER.name, c.role)

    """
    Method remove_collaborator
    """

    def test_cannot_remove_collaborator_because_is_not_already_one(self):
        user = get_user_model().objects.get(pk=2)
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(0, self.private_course.collaborators.count())
        with self.assertRaises(UserNotCollaboratorError):
            self.private_course.remove_collaborator(user)
        self.assertNotIn(user, self.private_course.collaborators.all())
        self.assertEqual(0, self.private_course.collaborators.count())

    def test_remove_collaborator_from_course(self):
        user = get_user_model().objects.get(pk=3)
        ca = CourseCollaborator.objects.create(collaborator=user, course=self.public_course,
                                               role=CollaboratorRole.TEACHER.name)
        self.private_course.course_collaborators.add(ca)
        self.assertIn(user, self.private_course.collaborators.all())
        self.assertEqual(1, self.private_course.collaborators.count())
        self.private_course.remove_collaborator(user)
        self.assertEqual(0, self.private_course.collaborators.count())
        self.assertNotIn(user, self.private_course.collaborators.all())

    """
    Method add_activity
    """

    def test_cannot_add_activity_because_course_is_read_only(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        self.students_only_course.state = CourseState.ARCHIVED.name
        self.assertTrue(self.students_only_course.read_only)

        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())
        with self.assertRaises(ChangeActivityOnCourseError):
            self.students_only_course.add_activity(activity)
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())

    def test_cannot_add_activity_because_activity_is_already_linked(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        CourseActivity.objects.create(
            course=self.students_only_course, activity=activity, rank=5
        )
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())
        with self.assertRaises(ActivityAlreadyOnCourseError):
            self.students_only_course.add_activity(activity)
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())

    def test_cannot_add_activity_because_activity_cannot_be_reused(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
            reuse=ActivityReuse.NON_REUSABLE.name
        )
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())
        with self.assertRaises(ActivityNotReusableError):
            self.assertFalse(self.students_only_course.add_activity(activity))
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())

    def test_add_activity(self):
        activity = Activity.objects.create(
            id=99,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
        )
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())
        self.students_only_course.add_activity(activity)
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())

        activity = Activity.objects.create(
            id=98,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
        )
        self.students_only_course.add_activity(activity)
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(2, self.students_only_course.course_activities.count())

        activity = Activity.objects.create(
            id=97,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1),
        )
        self.students_only_course.add_activity(activity)
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(3, self.students_only_course.course_activities.count())

        self.assertEqual(1, self.students_only_course.course_activities.filter(activity_id=99).get().rank)
        self.assertEqual(2, self.students_only_course.course_activities.filter(activity_id=98).get().rank)
        self.assertEqual(3, self.students_only_course.course_activities.filter(activity_id=97).get().rank)

    """
    Method remove_activity
    """

    def test_cannot_remove_activity_because_course_is_read_only(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        CourseActivity.objects.create(
            course=self.students_only_course, activity=activity, rank=5
        )
        self.students_only_course.state = CourseState.ARCHIVED.name
        self.assertTrue(self.students_only_course.read_only)

        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())
        with self.assertRaises(ChangeActivityOnCourseError):
            self.students_only_course.remove_activity(activity)
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())

    def test_cannot_remove_activity_because_activity_is_not_linked_with_the_course(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())
        with self.assertRaises(ActivityIsNotLinkedWithThisCourseError):
            self.students_only_course.remove_activity(activity)
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())

    def test_remove_activity(self):
        activity = Activity.objects.create(
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        CourseActivity.objects.create(
            course=self.students_only_course, activity=activity, rank=5
        )
        self.assertIn(activity, self.students_only_course.activities)
        self.assertEqual(1, self.students_only_course.course_activities.count())
        self.students_only_course.remove_activity(activity)
        self.assertNotIn(activity, self.students_only_course.activities)
        self.assertEqual(0, self.students_only_course.course_activities.count())

    """
    Property activities
    """

    def test_activities(self):
        CourseActivity.objects.create(
            rank=1, course=self.students_only_course, activity=self.activity1
        )
        CourseActivity.objects.create(
            rank=2, course=self.students_only_course, activity=self.activity2
        )
        CourseActivity.objects.create(
            rank=3, course=self.students_only_course, activity=self.activity3
        )
        CourseActivity.objects.create(
            rank=4, course=self.students_only_course, activity=self.activity4
        )
        self.assertEqual(4, self.students_only_course.course_activities.count())
        rank = 1
        for activity in self.students_only_course.activities:
            self.assertIsInstance(activity, Activity)
            self.assertEqual(rank, CourseActivity.objects.filter(
                course=self.students_only_course, activity=activity
            ).get().rank)
            rank += 1

    def test_course_activities_ordered_by_rank(self):
        CourseActivity.objects.create(
            rank=1, course=self.students_only_course, activity=self.activity1
        )
        CourseActivity.objects.create(
            rank=2, course=self.students_only_course, activity=self.activity2
        )
        CourseActivity.objects.create(
            rank=3, course=self.students_only_course, activity=self.activity3
        )
        CourseActivity.objects.create(
            rank=4, course=self.students_only_course, activity=self.activity4
        )
        self.assertEqual(4, self.students_only_course.course_activities.count())
        rank = 1
        for course_activity in self.students_only_course.course_activities.all():
            self.assertEqual(rank, course_activity.rank)
            rank += 1

    """
    Property read_only
    """

    def test_read_only(self):
        for course in (self.public_course, self.collaborators_only_course,
                       self.students_only_course, self.private_course):
            course.state = CourseState.ARCHIVED.name
            self.assertTrue(course.read_only)

    """
    Others
    """

    def test_order_in_course_access(self):
        self.assertLess(CourseAccess.PUBLIC, CourseAccess.STUDENTS_ONLY)
        self.assertLess(CourseAccess.PUBLIC, CourseAccess.COLLABORATORS_ONLY)
        self.assertLess(CourseAccess.PUBLIC, CourseAccess.PRIVATE)
        self.assertLess(CourseAccess.STUDENTS_ONLY, CourseAccess.COLLABORATORS_ONLY)
        self.assertLess(CourseAccess.STUDENTS_ONLY, CourseAccess.PRIVATE)
        self.assertLess(CourseAccess.COLLABORATORS_ONLY, CourseAccess.PRIVATE)

        self.assertGreater(CourseAccess.PRIVATE, CourseAccess.COLLABORATORS_ONLY)
        self.assertGreater(CourseAccess.PRIVATE, CourseAccess.STUDENTS_ONLY)
        self.assertGreater(CourseAccess.PRIVATE, CourseAccess.PUBLIC)
        self.assertGreater(CourseAccess.COLLABORATORS_ONLY, CourseAccess.STUDENTS_ONLY)
        self.assertGreater(CourseAccess.COLLABORATORS_ONLY, CourseAccess.PUBLIC)
        self.assertGreater(CourseAccess.STUDENTS_ONLY, CourseAccess.PUBLIC)

        for func in [self.assertEqual, self.assertGreaterEqual, self.assertLessEqual]:
            func(CourseAccess.PUBLIC, CourseAccess.PUBLIC)
            func(CourseAccess.STUDENTS_ONLY, CourseAccess.STUDENTS_ONLY)
            func(CourseAccess.COLLABORATORS_ONLY, CourseAccess.COLLABORATORS_ONLY)
            func(CourseAccess.PRIVATE, CourseAccess.PRIVATE)

    def test_reorder_activities(self):
        # Check that previous order is not changed
        for rank in range(1, 4):
            self.assertEqual(getattr(self, 'ca{}'.format(rank)).rank, rank * 10)

        # Reorder activities
        self.public_course.reorder_course_activities()

        # Check that new order is properly set
        rank = 1
        for ca in CourseActivity.objects.filter(course=self.public_course).all():
            self.assertEqual(ca.rank, rank)
            rank += 1

    def test_reorder_activities_nothing_to_do(self):
        # Reorder manually before calling the method
        rank = 1
        for ca in CourseActivity.objects.filter(course=self.public_course).all():
            ca.rank = rank
            rank += 1
            ca.save()

        # Check that reordering is correct
        rank = 1
        for ca in CourseActivity.objects.filter(course=self.public_course).all():
            self.assertEqual(ca.rank, rank)
            rank += 1

        # Reorder activities
        self.public_course.reorder_course_activities()

        # Check that new order is not changed
        rank = 1
        for ca in CourseActivity.objects.filter(course=self.public_course).all():
            self.assertEqual(ca.rank, rank)
            rank += 1

    """
    Method clean
    """

    def test_clean_error_registration_on_draft(self):
        self.public_course.registration_enabled = True
        self.public_course.state = CourseState.DRAFT.name
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_error_registration_on_archived(self):
        self.public_course.registration_enabled = True
        self.public_course.state = CourseState.ARCHIVED.name
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_error_access_private_state_published(self):
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.PRIVATE.name
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_error_access_collaborators_only_state_published(self):
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.COLLABORATORS_ONLY.name
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_error_author_in_students(self):
        user = self.public_course.author
        self.public_course.students.add(user)
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_error_author_in_collaborators(self):
        user = self.public_course.author
        CourseCollaborator.objects.create(
            collaborator=user,
            course=self.public_course,
            role=CollaboratorRole.TEACHER.name
        )
        with self.assertRaises(ValidationError):
            self.public_course.clean()

    def test_clean_access_students_only_state_published(self):
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.STUDENTS_ONLY.name
        self.public_course.clean()

    def test_clean_access_public_state_published(self):
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.PUBLIC.name
        self.public_course.clean()


class TestCourseManager(CourseTestCase):

    def test_get_public_courses(self):
        self.assertEqual(self.public_course.access, CourseAccess.PUBLIC.name)
        self.assertEqual(1, Course.objects.public().count())
        self.assertIn(self.public_course, Course.objects.public().all())
        self.assertNotIn(self.students_only_course, Course.objects.public().all())
        self.assertNotIn(self.collaborators_only_course, Course.objects.public().all())
        self.assertNotIn(self.private_course, Course.objects.public().all())

        self.students_only_course.access = CourseAccess.PUBLIC.name
        self.students_only_course.save()
        self.assertEqual(2, Course.objects.public().count())
        self.assertIn(self.public_course, Course.objects.public().all())
        self.assertIn(self.students_only_course, Course.objects.public().all())
        self.assertNotIn(self.collaborators_only_course, Course.objects.public().all())
        self.assertNotIn(self.private_course, Course.objects.public().all())

        self.collaborators_only_course.access = CourseAccess.PUBLIC.name
        self.collaborators_only_course.save()
        self.assertEqual(3, Course.objects.public().count())
        self.assertIn(self.public_course, Course.objects.public().all())
        self.assertIn(self.students_only_course, Course.objects.public().all())
        self.assertIn(self.collaborators_only_course, Course.objects.public().all())
        self.assertNotIn(self.private_course, Course.objects.public().all())

        self.private_course.access = CourseAccess.PUBLIC.name
        self.private_course.save()
        self.assertEqual(4, Course.objects.public().count())
        self.assertIn(self.public_course, Course.objects.public().all())
        self.assertIn(self.students_only_course, Course.objects.public().all())
        self.assertIn(self.collaborators_only_course, Course.objects.public().all())
        self.assertIn(self.private_course, Course.objects.public().all())

    def test_get_public_course_filter(self):
        self.assertEqual(self.public_course.access, CourseAccess.PUBLIC.name)
        self.students_only_course.access = CourseAccess.PUBLIC.name
        self.students_only_course.save()
        self.collaborators_only_course.access = CourseAccess.PUBLIC.name
        self.collaborators_only_course.save()
        self.private_course.access = CourseAccess.PUBLIC.name
        self.private_course.save()
        self.assertEqual(4, Course.objects.public().count())

        self.assertEqual(1, Course.objects.public(query="public").count())
        self.assertIn(self.public_course, Course.objects.public(query="public"))

        self.assertEqual(1, Course.objects.public(query="PUBLIC").count())
        self.assertIn(self.public_course, Course.objects.public(query="PUBLIC"))

    def test_get_written_by_courses(self):
        user = get_user_model().objects.get(pk=1)
        user_2 = get_user_model().objects.get(pk=2)
        self.assertEqual(4, Course.objects.written_by(user).count())

        self.collaborators_only_course.author = user_2
        self.collaborators_only_course.save()
        self.assertEqual(3, Course.objects.written_by(user).count())
        self.assertNotIn(self.collaborators_only_course, Course.objects.written_by(user).all())

    def test_get_written_by_courses_filter(self):
        user = get_user_model().objects.get(pk=1)
        self.assertEqual(4, Course.objects.written_by(user).count())

        self.assertEqual(1, Course.objects.written_by(user, query="public").count())
        self.assertIn(self.public_course, Course.objects.written_by(user, query="public"))

        self.assertEqual(1, Course.objects.written_by(user, query="PUBLIC").count())
        self.assertIn(self.public_course, Course.objects.written_by(user, query="PUBLIC"))

    def test_get_taught_by(self):
        teacher = get_user_model().objects.get(pk=2)
        self.collaborators_only_course.author = teacher
        self.collaborators_only_course.save()

        CourseCollaborator.objects.create(collaborator=teacher, course=self.public_course,
                                          role=CollaboratorRole.TEACHER.name)

        self.assertEqual(2, Course.objects.taught_by(teacher).count())
        self.assertIn(self.public_course, Course.objects.taught_by(teacher).all())
        self.assertIn(self.collaborators_only_course, Course.objects.taught_by(teacher).all())

    def test_get_taught_by_fitler(self):
        teacher = get_user_model().objects.get(pk=2)
        self.collaborators_only_course.author = teacher
        self.collaborators_only_course.save()

        CourseCollaborator.objects.create(collaborator=teacher, course=self.public_course,
                                          role=CollaboratorRole.TEACHER.name)

        self.assertEqual(1, Course.objects.taught_by(teacher, query="public").count())
        self.assertIn(self.public_course, Course.objects.taught_by(teacher, query="public").all())

        self.assertEqual(1, Course.objects.taught_by(teacher, query="PUBLIC").count())
        self.assertIn(self.public_course, Course.objects.taught_by(teacher, query="PUBLIC").all())

    def test_get_followed_by(self):
        s1 = get_user_model().objects.get(pk=2)
        RegistrationOnCourse.objects.create(course=self.public_course, student=s1)
        RegistrationOnCourse.objects.create(course=self.students_only_course, student=s1)
        RegistrationOnCourse.objects.create(course=self.collaborators_only_course, student=s1)
        self.assertEqual(3, Course.objects.followed_by(s1).count())
        self.assertIn(self.public_course, Course.objects.followed_by(s1).all())
        self.assertIn(self.students_only_course, Course.objects.followed_by(s1).all())
        self.assertIn(self.collaborators_only_course, Course.objects.followed_by(s1).all())

    def test_get_followed_by_filter(self):
        s1 = get_user_model().objects.get(pk=2)
        RegistrationOnCourse.objects.create(course=self.public_course, student=s1)
        RegistrationOnCourse.objects.create(course=self.students_only_course, student=s1)
        RegistrationOnCourse.objects.create(course=self.collaborators_only_course, student=s1)
        self.assertEqual(3, Course.objects.followed_by(s1).count())

        self.assertEqual(1, Course.objects.followed_by(s1, query="public").count())
        self.assertIn(self.public_course, Course.objects.followed_by(s1, query="public").all())

        self.assertEqual(1, Course.objects.followed_by(s1, query="PUBLIC").count())
        self.assertIn(self.public_course, Course.objects.followed_by(s1, query="PUBLIC").all())

    def test_get_recommendations_for_public_published_course_no_link(self):
        user = get_user_model().objects.get(pk=4)
        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.PUBLIC.name
        self.public_course.save()
        self.assertEqual(1, Course.objects.recommendations_for(user).count())
        self.assertIn(self.public_course, Course.objects.recommendations_for(user).all())

        self.public_course.state = CourseState.DRAFT.name
        self.public_course.access = CourseAccess.PUBLIC.name
        self.public_course.save()
        self.assertEqual(0, Course.objects.recommendations_for(user).count())
        self.assertNotIn(self.public_course, Course.objects.recommendations_for(user).all())

        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.STUDENTS_ONLY.name
        self.public_course.save()
        self.assertEqual(0, Course.objects.recommendations_for(user).count())
        self.assertNotIn(self.public_course, Course.objects.recommendations_for(user).all())

    def test_get_recommendations_for_public_published_not_as_author(self):
        self.assertEqual(0, Course.objects.recommendations_for(self.public_course.author).count())

    def test_get_recommendations_for_public_published_not_as_student(self):
        student = get_user_model().objects.get(pk=4)
        self.assertEqual(1, Course.objects.recommendations_for(student).count())
        self.assertIn(self.public_course, Course.objects.recommendations_for(student).all())
        RegistrationOnCourse.objects.create(course=self.public_course, student=student)
        self.assertEqual(0, Course.objects.recommendations_for(student).count())
        self.assertNotIn(self.public_course, Course.objects.recommendations_for(student).all())

    def test_get_recommendations_for_public_published_not_as_teacher(self):
        teacher = get_user_model().objects.get(pk=4)
        self.assertEqual(1, Course.objects.recommendations_for(teacher).count())
        self.assertIn(self.public_course, Course.objects.recommendations_for(teacher).all())
        CourseCollaborator.objects.create(course=self.public_course, collaborator=teacher)
        self.assertEqual(0, Course.objects.recommendations_for(teacher).count())
        self.assertNotIn(self.public_course, Course.objects.recommendations_for(teacher).all())

    def test_get_recommendations_for_filter(self):
        user = get_user_model().objects.get(pk=5)

        self.public_course.state = CourseState.PUBLISHED.name
        self.public_course.access = CourseAccess.PUBLIC.name
        self.public_course.save()

        self.students_only_course.state = CourseState.PUBLISHED.name
        self.students_only_course.access = CourseAccess.PUBLIC.name
        self.students_only_course.save()

        self.collaborators_only_course.state = CourseState.PUBLISHED.name
        self.collaborators_only_course.access = CourseAccess.PUBLIC.name
        self.collaborators_only_course.save()

        self.private_course.state = CourseState.PUBLISHED.name
        self.private_course.access = CourseAccess.PUBLIC.name
        self.private_course.save()

        self.assertEqual(4, Course.objects.recommendations_for(user).count())

        self.assertEqual(1, Course.objects.recommendations_for(user, query="public").count())
        self.assertIn(self.public_course, Course.objects.recommendations_for(user, query="public").all())

        self.assertEqual(1, Course.objects.recommendations_for(user, query="PUBLIC").count())
        self.assertIn(self.public_course, Course.objects.recommendations_for(user, query="PUBLIC").all())
