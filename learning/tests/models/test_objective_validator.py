#
# Copyright (C) 2020 Louis Barbier <louis.barbier@outlook.fr>
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
from django.test import TestCase

from learning.exc import ObjectiveIsAlreadyValidated, ObjectiveIsNotValidated
from learning.models import Course, CourseAccess, CourseState, Objective, TaxonomyLevel, \
    Activity, CourseObjective, ActivityObjective


class ObjectiveValidatorTestCase(TestCase):
    def setUp(self) -> None:
        self.user_owner = get_user_model().objects.create_user(id=1, username="isaac-newton")
        self.user_student = get_user_model().objects.create_user(id=2, username="napoleon-bonaparte")

        self.course = Course.objects.create(
            id=1,
            name="A simple private course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            tags="simple, course",
            access=CourseAccess.PRIVATE.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True
        )
        self.activity = Activity.objects.create(
            id=1,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=1)
        )
        self.objective = Objective.objects.create(
            ability="A simple ability",
            language="fr",
            author=self.user_owner,
        )


class TestObjectiveValidator(ObjectiveValidatorTestCase):
    def test_add_validator(self):
        self.objective.add_validator(self.user_student)
        self.assertIn(self.user_student, self.objective.validators.all())

    def test_add_validator_objective_already_validate(self):
        self.objective.add_validator(self.user_student)
        self.assertIn(self.user_student, self.objective.validators.all())
        with self.assertRaises(ObjectiveIsAlreadyValidated):
            self.objective.add_validator(self.user_student)

    def test_remove_validator(self):
        self.objective.add_validator(self.user_student)
        self.assertIn(self.user_student, self.objective.validators.all())
        self.objective.remove_validator(self.user_student)

    def test_remove_validator_not_validated(self):
        with self.assertRaises(ObjectiveIsNotValidated):
            self.objective.remove_validator(self.user_student)


class TestCourseObjectiveValidator(ObjectiveValidatorTestCase):
    def test_add_validator_on_course_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.course.objectives.filter(pk=self.objective.pk).get().add_validator(self.user_student)
        self.assertIn(self.user_student, self.course.objectives.filter(pk=self.objective.pk).get().validators.all())

    def test_add_already_validated_on_course_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.course.objectives.filter(pk=self.objective.pk).get().add_validator(self.user_student)
        self.assertIn(self.user_student, self.course.objectives.filter(pk=self.objective.pk).get().validators.all())
        with self.assertRaises(ObjectiveIsAlreadyValidated):
            self.course.objectives.filter(pk=self.objective.pk).get().add_validator(self.user_student)

    def test_remove_validator_on_course_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.course.objectives.filter(pk=self.objective.pk).get().add_validator(self.user_student)
        self.assertIn(self.user_student, self.course.objectives.filter(pk=self.objective.pk).get().validators.all())
        self.course.objectives.filter(pk=self.objective.pk).get().remove_validator(self.user_student)
        self.assertNotIn(self.user_student, self.course.objectives.filter(pk=self.objective.pk).get().validators.all())

    def test_remove_not_validated_on_course_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        with self.assertRaises(ObjectiveIsNotValidated):
            self.course.objectives.filter(pk=self.objective.pk).get().remove_validator(self.user_student)

    def test_objective_reusable_validated_on_both_entity(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())

    def test_objective_reusable_dont_validated_not_reusable_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=False)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertNotIn(self.user_student, self.activity_objective.validators.all())

    def test_objective_not_reusable_validate_reusable_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=False)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertNotIn(self.user_student, self.activity_objective.validators.all())

    def test_add_reusable_objective_already_validated(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.assertIn(self.user_student, self.activity_objective.validators.all())

    def test_objective_reusable_not_validated_on_both_entity(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()
        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()
        self.course_objective.change_validation(self.user_student)
        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())
        self.course_objective.change_validation(self.user_student)
        self.assertNotIn(self.user_student, self.course_objective.validators.all())
        self.assertNotIn(self.user_student, self.activity_objective.validators.all())

    def test_objective_reusable_dont_invalidate_not_reusable_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=False)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)
        self.activity_objective.change_validation(self.user_student)

        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())
        self.course_objective.change_validation(self.user_student)
        self.assertNotIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())

    def test_objective_not_reusable_dont_invalidate_reusable_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=False)
        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())
        self.assertIn(self.objective, self.activity.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)
        self.activity_objective.change_validation(self.user_student)

        self.assertIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())
        self.course_objective.change_validation(self.user_student)
        self.assertNotIn(self.user_student, self.course_objective.validators.all())
        self.assertIn(self.user_student, self.activity_objective.validators.all())

    def test_add_not_reusable_objective_where_objective_already_validated(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=True)
        self.assertIn(self.objective, self.course.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=False)

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.assertNotIn(self.user_student, self.activity_objective.validators.all())

    def test_add_not_reusable_objective_and_objective_already_validated_but_on_not_reusable_objective(self):
        self.course.add_objective(objective=self.objective,
                                  taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                  objective_reusable=False)
        self.assertIn(self.objective, self.course.objectives.all())

        self.course_objective = CourseObjective.objects.filter(course=self.course,
                                                               objective=self.objective).get()

        self.course_objective.change_validation(self.user_student)

        self.activity.add_objective(objective=self.objective,
                                    taxonomy_level=TaxonomyLevel.COMPREHENSION,
                                    objective_reusable=True)

        self.activity_objective = ActivityObjective.objects.filter(activity=self.activity,
                                                                   objective=self.objective).get()

        self.assertNotIn(self.user_student, self.activity_objective.validators.all())
