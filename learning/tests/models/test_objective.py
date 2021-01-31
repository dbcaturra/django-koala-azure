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

from learning.exc import ObjectiveAlreadyInModel, ObjectiveNotInModel
from learning.models import Objective, Course, CourseAccess, CourseState, TaxonomyLevel, Activity, Resource


class ObjectiveTestCase(TestCase):
    def setUp(self) -> None:
        get_user_model().objects.create_user(id=1, username="isaac-newton")
        get_user_model().objects.create_user(id=2, username="napoleon-bonaparte")

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

        self.resource = Resource.objects.create(
            author=get_user_model().objects.get(pk=1),
        )

        self.course_1 = Course.objects.create(
            id=2,
            name="A simple private course",
            description="A simple description",
            author=get_user_model().objects.get(pk=2),
            tags="simple, course",
            access=CourseAccess.PRIVATE.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True
        )
        self.activity_1 = Activity.objects.create(
            id=2,
            name="An activity",
            description="An activity description",
            author=get_user_model().objects.get(pk=2)
        )

        self.resource_1 = Resource.objects.create(
            author=get_user_model().objects.get(pk=2),
        )
        self.resource_2 = Resource.objects.create(
            author=get_user_model().objects.get(pk=2),
        )

        self.activity_1.add_resource(self.resource_1)
        self.activity_1.add_resource(self.resource_2)
        self.course_1.add_activity(activity=self.activity_1)


class CourseObjectiveTest(ObjectiveTestCase):
    def test_values_for_attributes(self):
        objective = Objective.objects.create(ability="Remember the main dates of the french revolution",
                                             language="en",
                                             author=get_user_model().objects.get(pk=2),
                                             )
        self.assertEquals(objective.ability, "Remember the main dates of the french revolution")
        self.assertEquals(objective.language, "en")
        self.assertEquals(objective.slug, "remember-the-main-dates-of-the-french-revolution")
        self.assertEquals(objective.author, get_user_model().objects.get(pk=2))

    def test_objective_course(self):
        objective = Objective.objects.create(ability="Remember the main dates of the french revolution",
                                             language="en",
                                             author=get_user_model().objects.get(pk=2),
                                             )
        self.course.add_objective(objective, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        self.assertIn(objective, self.course.objectives.all())

    def test_objective_remove_course(self):
        objective = Objective.objects.create(ability="Remember the main dates of the french revolution",
                                             language="en",
                                             author=get_user_model().objects.get(pk=2),
                                             )
        self.course.add_objective(objective, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        self.assertIn(objective, self.course.objectives.all())

        self.course.remove_objective(objective)
        self.assertNotIn(Objective, self.course.objectives.all())

    def test_objective_already_in_course(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the first world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )

        self.course.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        with self.assertRaises(ObjectiveAlreadyInModel):
            self.course.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

    def test_objective_not_in_course(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the second world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )
        with self.assertRaises(ObjectiveNotInModel):
            self.course.remove_objective(objective_1)

    def test_get_all_objectives(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the hundred war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )
        self.course_1.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        objective_2 = Objective.objects.create(ability="Remember the main dates of the american revolution",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )
        self.activity_1.add_objective(objective_2, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

        objective_3 = Objective.objects.create(ability="Remember the main dates of the seven year war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )
        self.resource_1.add_objective(objective_3, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

        objective_4 = Objective.objects.create(ability="Remember the main dates of the secession war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=2),
                                               )
        self.resource_2.add_objective(objective_4, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

        obj = self.course_1.get_all_objectives()

        self.assertIn(objective_1, obj)
        self.assertIn(objective_2, obj)
        self.assertIn(objective_3, obj)
        self.assertIn(objective_4, obj)


class ActivityObjectiveTest(ObjectiveTestCase):
    def test_objective_activity(self):
        objective = Objective.objects.create(ability="Remember the main dates of the Dreyfus affair",
                                             language="en",
                                             author=get_user_model().objects.get(pk=1),
                                             )
        self.activity.add_objective(objective, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        self.assertIn(objective, self.activity.objectives.all())

    def test_objective_already_in_activity(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the first world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=1),
                                               )

        self.activity.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        with self.assertRaises(ObjectiveAlreadyInModel):
            self.activity.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

    def test_objective_not_in_activity(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the second world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=1),
                                               )
        with self.assertRaises(ObjectiveNotInModel):
            self.activity.remove_objective(objective_1)


class ResourceObjectiveTest(ObjectiveTestCase):
    def test_objective_resource(self):
        objective = Objective.objects.create(ability="Remember the main dates of the french revolution",
                                             language="en",
                                             author=get_user_model().objects.get(pk=1),
                                             )
        self.resource.add_objective(objective, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        self.assertIn(objective, self.resource.objectives.all())

    def test_objective_already_in_resource(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the first world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=1),
                                               )

        self.resource.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)
        with self.assertRaises(ObjectiveAlreadyInModel):
            self.resource.add_objective(objective_1, taxonomy_level=TaxonomyLevel.KNOWLEDGE, objective_reusable=True)

    def test_objective_not_in_resource(self):
        objective_1 = Objective.objects.create(ability="Remember the main dates of the second world war",
                                               language="en",
                                               author=get_user_model().objects.get(pk=1),
                                               )
        with self.assertRaises(ObjectiveNotInModel):
            self.resource.remove_objective(objective_1)
