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
from django.test import TestCase, Client
from django.urls import reverse

from learning.forms import AddObjectiveForm, CourseObjectiveUpdateForm
from learning.tests.views.helpers import ClientFactory

from learning.models import Course, CourseAccess, CourseState, Objective, TaxonomyLevel, CourseObjective, \
    CollaboratorRole
from learning.views.objective import ObjectObjectiveUpdateValidationView, BasicModelDetailObjectiveRemoveView, \
    BasicModelDetailObjectiveUpdateView


class ObjectiveViews(TestCase):
    def setUp(self) -> None:
        get_user_model().objects.create_user(id=1, username="isaac-newton", password="pwd")
        get_user_model().objects.create_user(id=2, username="blase-pascal", password="pwd")
        get_user_model().objects.create_user(id=3, username="louis-xiv", password="pwd")
        get_user_model().objects.create_user(id=4, username="jules-ferry", password="pwd")

        self.objective = Objective.objects.create(ability="Remember the main dates of the french revolution",
                                                  language="en",
                                                  author=get_user_model().objects.get(pk=1))

        self.objective_1 = Objective.objects.create(ability="Remember the main dates of the "
                                                            "american revolution",
                                                    language="en",
                                                    author=get_user_model().objects.get(pk=2)
                                                    )
        self.public_course = Course.objects.create(
            id=1,
            name="A simple course",
            description="A simple description",
            author=get_user_model().objects.get(pk=1),
            access=CourseAccess.PUBLIC.name,
            state=CourseState.PUBLISHED.name,
            registration_enabled=True
        )
        self.public_course.tags.add("american", "revolution", "american revolution")
        self.public_course.add_objective(objective=self.objective,
                                         objective_reusable=True,
                                         taxonomy_level=TaxonomyLevel.COMPREHENSION
                                         )


class ObjectiveListTest(ObjectiveViews):
    def test_assert_list_objective_html(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:objective"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "learning/taxonomy/objective/my_list.html")
        content = response.content.decode("utf-8")
        self.assertIn("row-created-objective", content)
        self.assertIn("row-author-objective", content)
        self.assertIn("row-objective-ability", content)
        self.assertIn("button-create-new-objective", content)

    def test_assert_list_any_objective(self):
        Objective.objects.all().delete()
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:objective"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "learning/taxonomy/objective/my_list.html")
        content = response.content.decode("utf-8")
        self.assertNotIn("badge-created-by-objective", content)
        self.assertNotIn("badge-created-the-objective", content)
        self.assertNotIn("objective-ability", content)

    def test_button_in_any_objective(self):
        c = Client()
        response = c.get(path=reverse("learning:objective"))
        content = response.content.decode("utf-8")
        self.assertNotIn("button-create-new-objective", content)


class ObjectiveCreateTest(ObjectiveViews):
    def test_objective_create(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:objective/create"))
        content = response.content.decode("utf-8")
        self.assertIn("id_ability", content)
        self.assertIn("id_language", content)
        self.assertIn("add_objective_submit_button", content)


class CourseListObjectiveView(ObjectiveViews):
    def test_course_objective_list_view_owner(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/objectives", kwargs={'slug': self.public_course.slug}))
        content = response.content.decode("utf-8")
        self.assertTemplateUsed(response, "learning/course/details/objective.html")
        self.assertEquals(response.status_code, 200)
        self.assertIn("id-button-add-object-objective-modal", content)
        self.assertIn(self.objective.ability, content)

    def test_course_objective_list_view_not_owner(self):
        response = ClientFactory.get_client_for_user("blase-pascal").get(
            reverse("learning:course/detail/objectives", kwargs={'slug': self.public_course.slug}))
        content = response.content.decode("utf-8")
        self.assertTemplateUsed(response, "learning/course/details/objective.html")
        self.assertEquals(response.status_code, 200)
        self.assertNotIn("id-button-add-object-objective-modal", content)
        self.assertIn(self.objective.ability, content)


class CourseAddObjectiveView(ObjectiveViews):
    def test_course_objective_view_as_owner_new_ability(self):
        form_data = {
            'taxonomy_level': TaxonomyLevel.COMPREHENSION.name,
            'objective_reusable': False,
            'ability': 'My simple objective'
        }
        result = Objective.objects.most_relevant_objective_for_model(self.public_course)
        form = AddObjectiveForm(data=form_data)
        if result.count() > 0:
            form.fields['existing_ability'].choices = [('', 'Recommended objective exists but I create my own new '
                                                            'objective')] + [
                                                          (choice.id, choice.ability) for choice in result.all()]

        self.assertTrue(form.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/add", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertIn(Objective.objects.filter(ability='My simple objective').get(),
                      self.public_course.objectives.all())
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail/objectives", kwargs={'slug': self.public_course.slug})
        )

    def test_course_objective_view_as_owner_ability_exists(self):
        form_data = {
            'taxonomy_level': TaxonomyLevel.COMPREHENSION.name,
            'objective_reusable': False,
            'existing_ability': self.objective_1.id,
        }

        result = Objective.objects.most_relevant_objective_for_model(self.public_course)
        form = AddObjectiveForm(data=form_data)
        if result.count() > 0:
            form.fields['existing_ability'].choices = [('', 'Recommended objective exists but I create my own new '
                                                            'objective')] + [
                                                          (choice.id, choice.ability) for choice in result.all()]

        self.assertTrue(form.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/add", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertIn(self.objective_1,
                      self.public_course.objectives.all())
        self.assertRedirects(
            response,
            status_code=302, target_status_code=200,
            expected_url=reverse("learning:course/detail/objectives", kwargs={'slug': self.public_course.slug})
        )


class CourseRemoveObjectiveView(ObjectiveViews):
    def setUp(self) -> None:
        super().setUp()
        self.course_objective = CourseObjective.objects.create(objective=self.objective,
                                                               course=self.public_course,
                                                               taxonomy_level=TaxonomyLevel.APPLICATION,
                                                               objective_reusable=True)

    def test_object_objective_remove_as_course_owner(self):
        form_data = {
            'objective_pk': self.course_objective.id
        }
        form = BasicModelDetailObjectiveRemoveView.ObjectivePKForm(data=form_data)
        self.assertTrue(form.is_valid())

        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/remove", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertNotIn(self.course_objective.objective, self.public_course.objectives.all())

    def test_object_objective_remove_not_as_owner(self):
        form_data = {
            'objective_pk': self.course_objective.id
        }
        form = BasicModelDetailObjectiveRemoveView.ObjectivePKForm(data=form_data)
        self.assertTrue(form.is_valid())

        response = ClientFactory.get_client_for_user("blase-pascal").post(
            reverse("learning:course/detail/objective/remove", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 403)
        self.assertIn(self.course_objective.objective, self.public_course.objectives.all())

    def test_delete_object_objective_as_objective_owner(self):
        form_data = {
            'objective_pk': self.course_objective.objective.id
        }
        form = BasicModelDetailObjectiveRemoveView.ObjectivePKForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn(self.objective, Objective.objects.all())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:objective/delete"),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertNotIn(self.objective, Objective.objects.all())

    def test_delete_object_objective_not_as_objective_owner(self):
        form_data = {
            'objective_pk': self.course_objective.objective.id
        }
        form = BasicModelDetailObjectiveRemoveView.ObjectivePKForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIn(self.objective, Objective.objects.all())
        response = ClientFactory.get_client_for_user("blase-pascal").post(
            reverse("learning:objective/delete"),
            form_data
        )
        self.assertEquals(response.status_code, 403)
        self.assertIn(self.objective, Objective.objects.all())


class CourseObjectiveUpdateView(ObjectiveViews):
    def setUp(self) -> None:
        super().setUp()
        self.objective_3 = Objective.objects.create(ability="Remember the main dates of the "
                                                            "irish revolution",
                                                    language="en",
                                                    author=get_user_model().objects.get(pk=1)
                                                    )
        self.course_objective = CourseObjective.objects.create(objective=self.objective_3,
                                                               course=self.public_course,
                                                               taxonomy_level=TaxonomyLevel.APPLICATION,
                                                               objective_reusable=True
                                                               )
        self.course_objective_not_author = CourseObjective.objects.create(objective=self.objective_1,
                                                                          course=self.public_course,
                                                                          taxonomy_level=TaxonomyLevel.APPLICATION,
                                                                          objective_reusable=True)

    def test_update_view_for_owner_not_objective_author_change_taxonomy_level(self):
        form_data = {
            'objective_pk': self.course_objective_not_author.id,
            'taxonomy_level': TaxonomyLevel.EVALUATION.name,
            'objective_reusable': self.course_objective_not_author.objective_reusable
        }
        form = BasicModelDetailObjectiveUpdateView.ObjectivePKForm(data=form_data)
        form_objective = CourseObjectiveUpdateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form_objective.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(CourseObjective.objects.filter(objective=self.objective_1,
                                                         course=self.public_course).get().taxonomy_level,
                          TaxonomyLevel.EVALUATION.name)

    def test_update_view_for_owner_not_objective_author_change_objective_reusable(self):
        form_data = {
            'objective_pk': self.course_objective_not_author.id,
            'taxonomy_level': self.course_objective_not_author.taxonomy_level.name,
            'objective_reusable': False,
        }
        form = BasicModelDetailObjectiveUpdateView.ObjectivePKForm(data=form_data)
        form_objective = CourseObjectiveUpdateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form_objective.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertFalse(CourseObjective.objects.filter(objective=self.objective_1,
                                                        course=self.public_course).get().objective_reusable)

    def test_update_view_for_owner_but_not_objective_author_so_cant_change_ability(self):
        form_data = {
            'objective_pk': self.course_objective_not_author.id,
            'taxonomy_level': self.course_objective_not_author.taxonomy_level.name,
            'objective_reusable': False,
            'ability': 'Aahaha i am a little hacker'
        }
        form = BasicModelDetailObjectiveUpdateView.ObjectivePKForm(data=form_data)
        form_objective = CourseObjectiveUpdateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form_objective.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(CourseObjective.objects.filter(objective=self.objective_1,
                                                         course=self.public_course).get().objective.ability,
                          self.course_objective_not_author.objective.ability)

    def test_update_view_for_owner_who_is_objective_author_and_change_ability(self):
        form_data = {
            'objective_pk': self.course_objective.id,
            'taxonomy_level': self.course_objective.taxonomy_level.name,
            'objective_reusable': False,
            'ability': 'Knowing the main date of soviet revolution'
        }
        form = BasicModelDetailObjectiveUpdateView.ObjectivePKForm(data=form_data)
        form_objective = CourseObjectiveUpdateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertTrue(form_objective.is_valid())
        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertEquals(CourseObjective.objects.filter(objective=self.objective_3,
                                                         course=self.public_course).get().objective.ability,
                          'Knowing the main date of soviet revolution')


class CourseValidateObjectiveTest(ObjectiveViews):
    def test_course_objective_validation(self):
        course_objective = CourseObjective.objects.create(objective=self.objective,
                                                          course=self.public_course,
                                                          taxonomy_level=TaxonomyLevel.APPLICATION,
                                                          objective_reusable=True)
        form_data = {
            "pk_object_objective": course_objective.id
        }
        form = ObjectObjectiveUpdateValidationView.ValidationObjectivePKForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Test user validate

        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/validation/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertIn(get_user_model().objects.filter(pk=1).get(), course_objective.validators.all())

        # Test user invalidate

        response = ClientFactory.get_client_for_user("isaac-newton").post(
            reverse("learning:course/detail/objective/validation/change", kwargs={'slug': self.public_course.slug}),
            form_data
        )
        self.assertEquals(response.status_code, 302)
        self.assertNotIn(get_user_model().objects.filter(pk=1).get(), course_objective.validators.all())


class CourseViewObjectiveListTest(ObjectiveViews):
    def test_course_detail_objective_list_as_visitor(self):
        self.public_course.add_objective(objective=self.objective_1,
                                         objective_reusable=True,
                                         taxonomy_level=TaxonomyLevel.EVALUATION
                                         )
        self.anon_client = Client()
        response = self.anon_client.get(reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)
        for objective in self.public_course.objectives.all():
            self.assertIn("tr-table-object-objective-{}".format(objective.slug), content)
            self.assertIn("td-object-objective-{}-taxonomy-level".format(objective.slug), content)
            self.assertIn("td-object-objective-{}-ability".format(objective.slug), content)
            self.assertIn("td-object-objective-{}-created".format(objective.slug), content)
            # Checking that owner information are not here

            self.assertNotIn("td-object-objective-{}-update-validation-form".format(objective.slug), content)
            self.assertNotIn("pk_object_objective-validation-{}".format(objective.slug), content)
            self.assertNotIn("button-invalidate-objective-{}".format(objective.slug), content)
            self.assertNotIn("button-validate-objective-{}".format(objective.slug), content)

            # Check if owner form is here
            self.assertNotIn("td-object-objective-{}-author".format(objective.slug), content)
            self.assertNotIn("td-object-objective-{}-modification-panel".format(objective.slug), content)

    def test_course_detail_objective_list_as_student_with_objective_validated(self):
        registered_user = get_user_model().objects.filter(pk=3).get()
        course_objective_validated = CourseObjective.objects.filter(course=self.public_course,
                                                                    objective=self.objective).get()
        course_objective_validated.change_validation(registered_user)

        response = ClientFactory.get_client_for_user("louis-xiv").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)

        # Checking basic information on objective
        self.assert_basic_information_for_student(content, self.objective)

        # Check the objective validation button
        self.assertIn("button-invalidate-objective-{}".format(self.objective.slug), content)
        self.assertNotIn("button-validate-objective-{}".format(self.objective.slug), content)

        # Checking that owner information are not here
        self.assertNotIn("td-object-objective-{}-author".format(self.objective.slug), content)
        self.assertNotIn("td-object-objective-{}-modification-panel".format(self.objective.slug), content)

    def test_course_detail_objective_list_as_student_with_objective_invalidated(self):
        self.public_course.remove_objective(objective=self.objective)
        self.public_course.add_objective(objective=self.objective_1,
                                         objective_reusable=True,
                                         taxonomy_level=TaxonomyLevel.EVALUATION
                                         )
        response = ClientFactory.get_client_for_user("louis-xiv").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)

        # Checking basic information on objective
        self.assert_basic_information_for_student(content, self.objective_1)

        # Check the objective validation button
        self.assertIn("button-validate-objective-{}".format(self.objective_1.slug), content)
        self.assertNotIn("button-invalidate-objective-{}".format(self.objective_1.slug), content)

        # Checking that owner information are not here
        self.assertNotIn("td-object-objective-{}-author".format(self.objective_1.slug), content)
        self.assertNotIn("td-object-objective-{}-modification-panel".format(self.objective_1.slug), content)

    def assert_basic_information_for_student(self, content, objective):
        self.assertIn("tr-table-object-objective-{}".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-taxonomy-level".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-ability".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-created".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-update-validation-form".format(objective.slug), content)
        self.assertIn("pk_object_objective-validation-{}".format(objective.slug), content)

    def test_course_detail_objective_list_as_owner_but_not_as_objective_author(self):
        self.public_course.remove_objective(self.objective)
        self.public_course.add_objective(objective=self.objective_1,
                                         objective_reusable=True,
                                         taxonomy_level=TaxonomyLevel.EVALUATION
                                         )

        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)
        self.assert_basic_test_for_owner(content, self.objective_1)
        self.assertNotIn("author-of-objective-change-fields", content)

        # Check that user can't delete objective
        self.assertNotIn("form-delete-object-objective-{}".format(self.objective_1.slug), content)
        self.assertNotIn("objective-delete-{}-pk".format(self.objective_1.slug), content)
        self.assertNotIn("object-objective-{}-delete".format(self.objective_1.slug), content)

    def test_course_detail_objective_list_as_owner_as_objective_author(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)

        self.assert_basic_test_for_owner(content, self.objective)
        self.assertIn("author-of-objective-change-fields", content)

        # Check that user can delete objective
        self.assertIn("form-delete-object-objective-{}".format(self.objective.slug), content)
        self.assertIn("objective-delete-{}-pk".format(self.objective.slug), content)
        self.assertIn("object-objective-{}-delete".format(self.objective.slug), content)

    def test_course_detail_objective_list_as_teacher(self):
        self.public_course.add_collaborator(get_user_model().objects.filter(username="jules-ferry").get(),
                                            role=CollaboratorRole.TEACHER)
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.collaborators.all())
        response = ClientFactory.get_client_for_user("jules-ferry").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)

        # Assert teacher has not student
        self.assertNotIn("td-object-objective-{}-update-validation-form".format(self.objective.slug), content)
        self.assertNotIn("pk_object_objective-validation-{}".format(self.objective.slug), content)
        self.assertNotIn("button-invalidate-objective-{}".format(self.objective.slug), content)
        self.assertNotIn("button-validate-objective-{}".format(self.objective.slug), content)

        self.assertIn("id-button-change-object-objective-modal-{}".format(self.objective.slug), content)
        self.assertIn("change-object-objective-{}-pk".format(self.objective.slug), content)
        self.assertIn("id_taxonomy_level".format(self.objective.slug), content)
        self.assertIn("id_objective_reusable", content)
        self.assertIn("change-object-objective-{}-submit".format(self.objective.slug), content)

        # Check that user can't delete objective
        self.assertNotIn("form-delete-object-objective-{}".format(self.objective.slug), content)
        self.assertNotIn("objective-delete-{}-pk".format(self.objective.slug), content)
        self.assertNotIn("object-objective-{}-delete".format(self.objective.slug), content)

    def test_course_detail_objective_list_as_non_editor_teacher(self):
        self.public_course.add_collaborator(get_user_model().objects.filter(username="jules-ferry").get(),
                                            role=CollaboratorRole.NON_EDITOR_TEACHER)
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.collaborators.all())
        response = ClientFactory.get_client_for_user("jules-ferry").get(
            reverse("learning:course/detail", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("learning/detail.html")

        content = response.content.decode("utf-8")
        # Checking if table is here
        self.assertIn("table-object-objective-list", content)

        # Assert teacher has not student
        self.assertNotIn("td-object-objective-{}-update-validation-form".format(self.objective.slug), content)
        self.assertNotIn("pk_object_objective-validation-{}".format(self.objective.slug), content)
        self.assertNotIn("button-invalidate-objective-{}".format(self.objective.slug), content)
        self.assertNotIn("button-validate-objective-{}".format(self.objective.slug), content)

        self.assertNotIn("id-button-change-object-objective-modal-{}".format(self.objective.slug), content)
        self.assertNotIn("change-object-objective-{}-pk".format(self.objective.slug), content)
        self.assertNotIn("id_taxonomy_level".format(self.objective.slug), content)
        self.assertNotIn("id_objective_reusable", content)
        self.assertNotIn("change-object-objective-{}-submit".format(self.objective.slug), content)

        # Check that user can't delete objective
        self.assertNotIn("form-delete-object-objective-{}".format(self.objective.slug), content)
        self.assertNotIn("objective-delete-{}-pk".format(self.objective.slug), content)
        self.assertNotIn("object-objective-{}-delete".format(self.objective.slug), content)

    def assert_basic_test_for_owner(self, content, objective):
        # Check that global information are displayed
        self.assertIn("tr-table-object-objective-{}".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-taxonomy-level".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-ability".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-created".format(objective.slug), content)

        # checking that student actions are not displayed
        self.assertNotIn("td-object-objective-{}-update-validation-form".format(objective.slug), content)
        self.assertNotIn("pk_object_objective-validation-{}".format(objective.slug), content)
        self.assertNotIn("button-invalidate-objective-{}".format(objective.slug), content)
        self.assertNotIn("button-validate-objective-{}".format(objective.slug), content)

        # Checking that owner information are displayed
        self.assertIn("td-object-objective-{}-author".format(objective.slug), content)
        self.assertIn("td-object-objective-{}-modification-panel".format(objective.slug), content)
        self.assertIn("id-button-remove-object-objective-modal-{}".format(objective.slug), content)

        # Checking that objective removing is displayed for entity author
        self.assertIn("form-remove-object-objective-{}".format(objective.slug), content)
        self.assertIn("objective-remove-{}-pk".format(objective.slug), content)
        self.assertIn("object-objective-{}-remove".format(objective.slug), content)

        # Checking that objective change is displayed for entity author
        self.assertIn("id-button-change-object-objective-modal-{}".format(objective.slug), content)
        self.assertIn("change-object-objective-{}-pk".format(objective.slug), content)
        self.assertIn("id_taxonomy_level".format(objective.slug), content)
        self.assertIn("id_objective_reusable", content)
        self.assertIn("change-object-objective-{}-submit".format(objective.slug), content)


class CourseProgression(ObjectiveViews):

    def test_student_progression_for_visitor(self):
        """Test that off line student has been redirected"""
        self.anon_client = Client()
        response = self.anon_client.get(
            reverse("learning:course/detail/progression/student", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 302)

    def test_teacher_progression_for_visitor(self):
        self.anon_client = Client()
        response = self.anon_client.get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEqual(response.status_code, 302)

    def test_student_progression_for_student(self):
        response = ClientFactory.get_client_for_user("louis-xiv").get(
            reverse("learning:course/detail/progression/student", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)

    def test_teacher_progression_for_student(self):
        response = ClientFactory.get_client_for_user("louis-xiv").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 403)

    def test_student_progression_for_author(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/student", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)

    def test_teacher_progression_for_author(self):
        self.public_course.register(get_user_model().objects.filter(username="jules-ferry").get())
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.students.all())
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn(
            "student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertNotIn(
            "student-{}-list".format(get_user_model().objects.filter(username="louis-xiv").get().id), content)
        self.assertIn("alert-you-must-select-an-user",content)

    def test_teacher_progression_for_teacher_non_editor(self):
        self.public_course.register(get_user_model().objects.filter(username="jules-ferry").get())
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.students.all())
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn(
            "student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertNotIn(
            "student-{}-list".format(get_user_model().objects.filter(username="louis-xiv").get().id), content)

    def test_teacher_progression_for_teacher_editor(self):
        self.public_course.register(get_user_model().objects.filter(username="jules-ferry").get())
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.students.all())
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn(
            "student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertNotIn(
            "student-{}-list".format(get_user_model().objects.filter(username="louis-xiv").get().id), content)

    def test_teacher_progression_for_teacher_owner(self):
        self.public_course.register(get_user_model().objects.filter(username="jules-ferry").get())
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.students.all())
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn(
            "student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertNotIn(
            "student-{}-list".format(get_user_model().objects.filter(username="louis-xiv").get().id), content)

    def test_teacher_student_registered_progression_for_teacher_owner(self):
        self.public_course.register(get_user_model().objects.filter(username="jules-ferry").get())
        self.assertIn(get_user_model().objects.filter(username="jules-ferry").get(),
                      self.public_course.students.all())
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher/",
                    kwargs={'slug': self.public_course.slug, 'username_id': get_user_model().objects.filter(
                        username="jules-ferry").get().id}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn(
            "active-student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertIn(self.objective.ability, content)
        object_objective = CourseObjective.objects.filter(objective=self.objective, course=self.public_course).get()
        self.assertIn(object_objective.taxonomy_level, content)
        self.assertIn("Working", content)

    def test_teacher_student_not_registered_progression_for_teacher_owner(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher/",
                    kwargs={'slug': self.public_course.slug, 'username_id': get_user_model().objects.filter(
                        username="jules-ferry").get().id}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("alert-user-is-not-registered", content)

    def test_teacher_any_student_registered(self):
        response = ClientFactory.get_client_for_user("isaac-newton").get(
            reverse("learning:course/detail/progression/teacher", kwargs={'slug': self.public_course.slug}))
        self.assertEquals(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertNotIn(get_user_model().objects.filter(username="jules-ferry").get().id,
                         self.public_course.students.all())
        self.assertNotIn(
            "active-student-{}-list".format(get_user_model().objects.filter(username="jules-ferry").get().id), content)
        self.assertIn("alert-any-user-registered", content)

