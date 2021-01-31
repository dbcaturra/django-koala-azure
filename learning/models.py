#
# Copyright (C) 2019-2020 Guillaume Bernard <guillaume.bernard@koala-lms.org>
#
# Copyright (C) 2020 Loris Le Bris <loris.le_bris@etudiant.univ-lr.fr>
# Copyright (C) 2020 Arthur Baribeaud <arthur.baribeaud@etudiant.univ-lr.fr>
# Copyright (C) 2020 Alexis Delabarre <alexis.delabarre@etudiant.univ-lr.fr>
# Copyright (C) 2020 Célian Rolland <celian.rolland@etudiant.univ-lr.fr>
# Copyright (C) 2020 Raphaël Penault <raphael.penault@etudiant.univ-lr.fr>
# Copyright (C) 2020 Dervin Enard <dervin@hotmail.fr>
# Copyright (C) 2020 Olivia Bove <olivia.bove@hotmail.fr>
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
import abc
import itertools
import os
import unicodedata
from enum import Enum
from typing import Generator, List, Tuple, Set

from django.conf import global_settings, settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, QuerySet, Q
from django.template.defaultfilters import filesizeformat
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _, gettext_noop, get_language
from django.utils.translation import pgettext_lazy
from taggit.managers import TaggableManager

import learning.exc
from learning import logger
from learning.permissions import ObjectPermissionManagerMixin

# Translate course, activity or resource in order to use them dynamically
gettext_noop("course")
gettext_noop("Course")
gettext_noop("resource")
gettext_noop("Resource")
gettext_noop("activity")
gettext_noop("Activity")


def get_max_upload_size() -> int:
    """
    Get the maximum authorized upload size for a resource. By default, it uses the “LEARNING_UPLOAD_SIZE” settings.
    Otherwise, it sets a default value, in bytes.

    :return: the maximum, authorized, upload size, in bytes
    :rtype: int
    """
    try:
        upload_size = settings.LEARNING_UPLOAD_SIZE
    except AttributeError:
        upload_size = 2 ** 20  # 1Mio
    return upload_size


def get_translated_languages() -> List[Tuple[str, str]]:
    """
    Get the list of languages supported by Django, translated in the current locale.

    .. note:: Languages are wrapped around the “gettext_noop” function which does not translate them at runtime.

    :return: a list of tuples containing the language code and the translated version of the language name
    :rtype: list of tuples
    """
    languages = []
    for code, language in global_settings.LANGUAGES:
        languages.append((code, _(language)))
    return languages


def generate_slug_for_model(model, instance: "models.Model") -> str:
    """
    Generate a slug value for a specific instance. It is made to avoid duplicates, as slugs are unique. \
    In case of two instance having the same slug_value, hence the same slug, a counter is added at the end \
    of the slug.

    :param model: the concrete model of the instance
    :type model: class
    :param instance: an instance of a ObjectWithSlugMixin
    :type instance: ObjectWithSlugMixin
    :return: a slug made from the instance
    :rtype: str
    """
    max_length = getattr(model, "_meta").get_field("slug").max_length
    slug = instance.slug = original_slug = slugify(instance.slug_generator())[:max_length]

    # If necessary, add an index (1, 2, etc.) to the slug field if another Resource exists
    # with the same slug
    for counter in itertools.count(1):
        # noinspection PyUnresolvedReferences
        if not model.objects.filter(slug=slug).exclude(pk=instance.id).exists():
            break  # The slug is not used by another resource
        slug = "{slug}-{counter}".format(slug=original_slug[:max_length - len(str(counter)) - 1], counter=counter)
    return slug


class OrderedEnum(Enum):
    """
    Special enumeration which can has ordered elements. Each literal has a weight which is used to compare with others.

    .. warning:: Literals are tuples with a value and a weight, like:
        A = ("A", 0)
        B = ("B", 1
    """

    # pylint: disable=unused-argument
    # noinspection PyUnusedLocal
    def __init__(self, token: str, weight: int):
        self.__weight = weight

    @property
    def weight(self) -> int:
        """
        Get the enumeration literal weight.

        :return: the enumeration literal weight
        :rtype: int
        """
        return self.__weight

    @property
    def value(self) -> str:
        """
        Get the enumeration literal value (the string part of the tuple)

        :return: the enumeration literal value
        :rtype: str
        """
        return super().value[0]

    def __eq__(self, other):
        return self.weight == other.weight

    def __lt__(self, other):
        return self.weight < other.weight

    def __gt__(self, other):
        return self.weight > other.weight

    def __le__(self, other):
        return self.weight <= other.weight

    def __ge__(self, other):
        return self.weight >= other.weight


class Licences(OrderedEnum):
    """
    Authorised licences that can be used in resources. The elements are ordered according to the degree of freedom to
    use content.
    """
    CC_0 = (_("Creative Commons 0 (Public domain)"), 0)
    CC_BY = (_("Creative Commons Attribution"), 1)
    CC_BY_SA = (_("Creative Commons Attribution, Share Alike"), 2)
    CC_BY_NC = (_("Creative Commons Attribution, Non Commercial"), 3)
    CC_BY_NC_SA = (_("Creative Commons Attribution, Non Commercial, Share Alike"), 4)
    CC_BY_ND = (_("Creative Commons Attribution, No Derivatives"), 5)
    CC_BY_NC_ND = (_("Creative Commons Attribution, No Commercial, No Derivatives"), 6)
    NA = (_("Not appropriate"), 7)
    ALL_RIGHTS_RESERVED = (_("All rights reserved"), 8)


class Duration(OrderedEnum):
    """
    The different allowed duration that are attached to elements to indicate how long it takes to view them.
    """
    FIVE_OR_LESS = (_("Less than 5 minutes"), 0)
    TEN_OR_LESS = (_("Less than 10 minutes"), 0)
    FIFTEEN_OR_LESS = (_("Less than 15 minutes"), 1)
    TWENTY_OR_LESS = (_("Less than 20 minutes"), 1)
    TWENTY_FIVE_OR_LESS = (_("Less than 25 minutes"), 2)
    THIRTY_OR_MORE = (_("30 minutes or more"), 2)
    NOT_SPECIFIED = (_("Not specified"), 3)


class ResourceAccess(OrderedEnum):
    """
    Defines the different access rights for resources.
    """
    PUBLIC = (_("Public"), 0)
    EXISTING_ACTIVITIES = (_("Only in activities"), 1)
    COLLABORATORS_ONLY = (_("Collaborators only"), 2)
    PRIVATE = (_("Private"), 3)


class ResourceReuse(OrderedEnum):
    """
    Defines the different reuse rights for resources.
    """
    NO_RESTRICTION = (_("Reusable"), 0)
    ONLY_AUTHOR = (_("Author only"), 1)
    NON_REUSABLE = (_("Non reusable"), 2)


class ResourceType(Enum):
    """
    The resource type. Each type has a specific icon name from Fontawesome. It is used to display the icon
    alongside the resource type.
    """
    FILE = (_("File"), "fa-file-alt")
    VIDEO = (_("Video"), "fa-video")
    AUDIO = (_("Audio"), "fa-broadcast-tower")

    # noinspection PyUnusedLocal
    # pylint: disable=unused-argument
    def __init__(self, i18n_str: str, fa_icon: str):
        self.__icon = fa_icon

    @property
    def icon(self) -> str:  # pragma: no cover
        """
        Get the Fontawesome icon name.

        :return: the icon name
        :rtype: str
        """
        return self.__icon

    @property
    def value(self) -> str:
        """
        Get the resource type

        :return: the resource type
        :rtype: str
        """
        return super().value[0]


class TaxonomyLevel(OrderedEnum):
    """
    The enumeration of taxonomy level
    First: The value, which is the name of the level
    Second: The level, the position in the taxonomy
    For further information, check the Bloom Taxonomy:
    https://en.wikipedia.org/wiki/Bloom%27s_taxonomy
    """
    KNOWLEDGE = (_("Knowledge"), 1)
    COMPREHENSION = (_("Comprehension"), 2)
    APPLICATION = (_("Application"), 3)
    ANALYSIS = (_("Analysis"), 4)
    SYNTHESIS = (_("Synthesis"), 5)
    EVALUATION = (_("Evaluation"), 6)

    @property
    def value(self):
        return super().value[0]

    def level(self):
        return super().value[1]


class ObjectWithSlugMixin:
    """
    This class is obsolete but required because referenced in migrations.
    """


class CollaboratorRole(Enum):
    """
    The most basic roles for collaborators.
    """
    TEACHER = _("Teacher")
    NON_EDITOR_TEACHER = _("Non-editor Teacher")
    OWNER = _("Owner")


PERMISSIONS_FOR_ROLE = {
    "students": ["view", "view_similar"],
    CollaboratorRole.TEACHER.name: [
        "view", "view_hidden", "view_similar", "add", "change", "view_collaborators", "view_students", "add_student",
        "change_student", "delete_student", "add_objective", "view_objective", "delete_objective", "change_objective",
    ],
    CollaboratorRole.NON_EDITOR_TEACHER.name: [
        "view", "view_hidden", "view_similar", "view_collaborators", "view_students", "view_objective"
    ],
    CollaboratorRole.OWNER.name: [
        "view", "view_hidden", "view_similar", "add", "change", "delete",
        "change_privacy",
        "view_students", "add_student", "change_student", "delete_student",
        "view_collaborators", "add_collaborator", "change_collaborator", "delete_collaborator",
        "add_objective", "view_objective", "delete_objective", "change_objective",
    ]
}


class ObjectiveManager(models.Manager):
    """
    The manager that manage objectives
    """

    def most_relevant_objective_for_model(self, basic_model_mixin_object) -> QuerySet:
        """
        This method search all objectives in the database that can deal with the course/activity/resource passed in
        parameter
        todo: Improving the research algorithm. Refine searches
        :param basic_model_mixin_object: BasicModelMixin instance
        :return QuerySet(): A query-set that contains all most relevant course_objective
        """
        # A list that contains all primary keys of relevant objectives
        objectives_primary_keys_list = []

        def handle_objective_research(target_object):
            objective_filtered_by_tags_in_common_with_other_entity = \
                [obj.course_objective for obj in target_object.objects.all()
                 if any(''.join(
                    (c for c in unicodedata.normalize('NFD', name.lower())
                     if unicodedata.category(c) != 'Mn')) in ''.join(
                    (c for c in unicodedata.normalize('NFD', obj.related_entity.name.lower())
                     if unicodedata.category(c) != 'Mn'))
                        for name in basic_model_mixin_object.tags.names())]
            return objective_filtered_by_tags_in_common_with_other_entity

        if basic_model_mixin_object.tags.all().count() > 0:
            objective_filtered_by_tags_in_ability = \
                [obj for obj in Objective.objects.all()
                 if any(''.join((c for c in unicodedata.normalize('NFD', name.lower())
                                 if unicodedata.category(c) != 'Mn')) in ''.join(
                    (c for c in unicodedata.normalize('NFD', obj.ability.lower())
                     if unicodedata.category(c) != 'Mn'))
                        for name in basic_model_mixin_object.tags.names())]

            objectives_filtered = \
                objective_filtered_by_tags_in_ability \
                + handle_objective_research(CourseObjective) \
                + handle_objective_research(ActivityObjective) \
                + handle_objective_research(ResourceObjective)

            objectives_primary_keys_list = [pk.id for pk in objectives_filtered]

        return self.filter(pk__in=objectives_primary_keys_list)


class Objective(models.Model):
    """
    The course_objective is an object which contains an ability.
    This object follow the student progression
    """
    ability = models.CharField(
        max_length=255,
        verbose_name=_("Ability"),
        help_text=_("A label that indicates the abilities validated by the learner."),
        blank=False,
        null=False
    )
    language = models.CharField(
        max_length=20,
        choices=get_translated_languages(),
        verbose_name=_("Language"),
        help_text=_("The language in which the course_objective is written in.")
    )
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="created_objectives",
        verbose_name=_("Author"),
        help_text=_("The course_objective’s author.")
    )
    validators = models.ManyToManyField(
        get_user_model(),
        through="ValidationOnObjective",
        related_name="validation_on_objective",
        verbose_name=_("Students validators"),
        help_text=_("The user that can validate the course_objective.")
    )
    objects = ObjectiveManager()

    slug = models.SlugField(unique=True)
    created = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Published the…"))
    updated = models.DateTimeField(auto_now_add=False, auto_now=True, verbose_name=_("Last updated the…"))

    def slug_generator(self):
        return self.ability

    def add_validator(self, student: get_user_model()) -> None:
        """
        Add a new student in the list of students that validated the course_objective.

        :param student: the student that wants to set this course_objective as validated
        :type student: get_user_model()

        :raises learning.exc.ObjectiveIsAlreadyValidated: when the student already validated this course_objective.
        """
        student_already_validated = student in self.validators.all()
        if student_already_validated:
            raise learning.exc.ObjectiveIsAlreadyValidated(
                _("The student {student} has already validated this course_objective.") % {"student": student}
            )
        self.validations.create(student=student)

    def remove_validator(self, student: get_user_model()) -> None:
        """
        Remove the given student from the list of students that validated the course_objective.

        :param student: the user student to remove
        :type student: get_user_model()

        :raises learning.exc.ObjectiveIsNotValidated: when the student did not validate the course_objective.
        """
        student_did_not_already_validate = student in self.validators.all()
        if not student_did_not_already_validate:
            raise learning.exc.ObjectiveIsNotValidated(
                _("The student %(student)s has not validated this course_objective yet.It cannot be removed "
                  "from students that validated the course_objective.") % {"student": student}
            )
        self.validations.filter(student=student).delete()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None) -> None:
        """
        save() method is overridden to generate the slug field.
        :return:
        """
        if Objective.objects.filter(ability=self.ability):
            raise learning.exc.ObjectiveAlreadyExists(
                _("The course_objective that you are trying to create already exists.")
            )
        self.slug = generate_slug_for_model(Objective, self)
        super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return self.ability

    def clean(self):
        if len(self.ability) == 0:
            raise learning.exc.ObjectiveAbilityCannotBeEmpty(_("The course_objective ability label cannot be empty."))


class ValidationOnObjective(models.Model):
    """
    A intermediary object to represent the validation on each course_objective.
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        verbose_name=_("Objective"),
        related_name="validations"
    )
    student = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("Student"),
        related_name="validations"
    )
    slug = models.SlugField(
        unique=True
    )
    validated_the = models.DateTimeField(
        auto_now_add=True,
        auto_now=False,
        verbose_name=_("Validated the…")
    )

    def slug_generator(self):
        return f"{self.objective.ability}-{str(self.student)}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None) -> None:
        """
        save() method is overridden to generate the slug field.
        """
        self.slug = generate_slug_for_model(ValidationOnObjective, self)
        super().save(force_insert, force_update, using, update_fields)


# noinspection PyAbstractClass
class BasicModelManager(models.Manager):
    """
    This is the basic manager used in CourseManager, ResourceManager and ActivityManager.
    """

    @abc.abstractmethod
    def public(self, **kwargs) -> QuerySet:
        """
        The BasicModel instances that are known to be public, so, that can be displayed to anyone without any required
        permission right.

        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: the public BasicModel’s instances
        :rtype: QuerySet
        """

    @abc.abstractmethod
    def recommendations_for(self, user: get_user_model(), **kwargs) -> QuerySet:
        """
        The BasicModel instance that are recommended for a specific user.

        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :param user: the user for which to get recommended entities.
        :type: get_user_model()

        :return: the recommended instances for the user.
        :rtype: QuerySet
        """

    # noinspection PyMethodMayBeStatic
    def _filter_with_query(self, queryset: QuerySet, query: str) -> QuerySet:
        """
        Filter a Object queryset with a query string. This filters name and description.

        .. note:: FIXME: this should maybe return an exception if it’s not working properly.

        :param queryset: the original queryset to filter
        :type queryset: QuerySet
        :param query: the query string
        :type query: str
        :return: a new queryset based on the original but filtered using the query parameter
        :rtype: QuerySet
        """
        if queryset and query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query))
        return queryset

    def written_by(self, author: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all objects written by the author. It sorts the results according to the updated property.

        :param author: a user that wrote courses
        :type author: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: all objects written by the author given in parameter
        :rtype: QuerySet
        """
        qs = super().get_queryset().filter(author=author).exclude(favourite_for=author)
        return self._filter_with_query(qs, kwargs.get("query", "")).order_by("-updated")

    def taught_by(self, teacher: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all objects taught by (as author or collaborator) a teacher.

        :param teacher: a user that teachers in objects
        :type teacher: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: all objects taught by the teacher
        :rtype: QuerySet
        """
        qs = super().get_queryset().filter(Q(author=teacher) | Q(collaborators=teacher))
        return self._filter_with_query(qs, kwargs.get("query", "")).distinct()

    def favourites_for(self, user: get_user_model()) -> QuerySet:
        """
        Get a Queryset object that includes all the entities set a favourite for a specific user.

        :param user: the user for which to get favourite entities
        :type user: get_user_model()
        :return: the QuerySet of favourite entities
        :rtype: QuerySet
        """
        return super().get_queryset().filter(favourite_for=user)

    def teacher_favourites_for(self, user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get a Queryset object that includes all the entities set a favourite for a specific user.

        :param user: the user for which to get favourite entities
        :type user: get_user_model()
        :return: the QuerySet of favourite entities
        :rtype: QuerySet
        """
        qs = super().get_queryset().filter(Q(author=user) | Q(collaborators=user), favourite_for=user)
        return self._filter_with_query(qs, kwargs.get("query", "")).distinct()

    def student_favourites_for(self, user: get_user_model()) -> QuerySet:
        """
        Get a Queryset object that includes all the entities set a favourite for a specific user.

        :param user: the user for which to get favourite entities
        :type user: get_user_model()
        :return: the QuerySet of favourite entities
        :rtype: QuerySet
        """
        return super().get_queryset().filter(favourite_for=user, students=user)


class BasicModelMixin(ObjectPermissionManagerMixin, models.Model):
    """
    This is the basic model used in Course, Resource and Activity. This groups fields in common.
    """

    @property
    @abc.abstractmethod
    def author(self) -> get_user_model():
        """
        Get the entity author. It is often defined explicitly in subclasses using a foreign key. This property, here,
        ensures that calling it from this class with not raise any syntax error.

        :return: the entity author
        :rtype: get_user_model()
        """

    @property
    @abc.abstractmethod
    def collaborators(self) -> QuerySet:
        """
        Get the entity collaborators. It is often defined explicitly in subclasses using foreign keys. This property,
         here, ensures that calling it from this class with not raise any syntax error.

        :return: the entity author
        :rtype: str
        """

    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("A title that clearly indicates the theme you are writing about.")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    language = models.CharField(
        max_length=20,
        choices=get_translated_languages(),
        verbose_name=_("Language"),
        help_text=_("The language in which the entity is written in."),
        default=get_language()
    )
    tags = TaggableManager(
        help_text=_("A set of coma separated keywords that describe the theme and permits this content to be found by "
                    "browsing or searching.")
    )
    favourite_for = models.ManyToManyField(
        get_user_model(),
        related_name="+",  # no reverse relation
        verbose_name=_("Favorite for users"),
    )

    """
    Auto-generated fields
    """
    slug = models.SlugField(unique=True)
    # noinspection PyArgumentEqualDefault
    published = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Published the…"))
    # noinspection PyArgumentEqualDefault
    updated = models.DateTimeField(auto_now_add=False, auto_now=True, verbose_name=_("Last updated the…"))

    def slug_generator(self) -> str:
        """
        Get the slug generator for this entity. It is the attribute that will be used to generate the object slug.

        .. note:: See the generate_slug_for_model() function to know how it work. It is used in the save() method of
                  models to dynamically generate their slugs.

        :return: the slug generator
        :rtype: str
        """
        return self.name

    @property
    @abc.abstractmethod
    def object_collaborators(self):
        """
        The collaborators related name (as declared in Course, Activity or Resource)

        :return: The RelatedManager that references the object collaborators
        :rtype: RelatedManager
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def object_objectives(self):
        """
        The objectives related name (as declared in Course, Activity or Resource)

        :return: The RelatedManager that references the object objectives
        :rtype: RelatedManager
        """
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def linked_objects(self) -> Generator["BasicModelMixin", None, None]:
        """
        The included objects in this object. For instance, a course has activities, while an activity has resources.

        :return: The Generator that references the included objects
        :rtype: Generator
        """
        raise NotImplementedError()

    def add_collaborator(self, collaborator: get_user_model(), role: CollaboratorRole) -> "ObjectCollaboratorMixin":
        """
        Add a collaborator on the object

        :raises UserIsAlreadyAuthor: when the user is already the author on the object
        :raises UserIsAlreadyCollaborator: when the user is already a collaborator on the object

        :param collaborator: the collaborator to add on the object
        :type collaborator: get_user_model()
        :param role: the role of the collaborator on the object
        :type role: CollaboratorRole

        :return: the newly created collaborator instance
        :rtype: ObjectCollaboratorMixin
        """
        user_is_collaborator = collaborator in self.collaborators.all()
        user_is_author = collaborator == self.author
        if user_is_author:
            raise learning.exc.UserIsAlreadyAuthor(
                _("The user “%(user)s” is already the author of this %(object)s. "
                  "The user %(user)s cannot be added as a collaborator.")
                % {"object": _(self.__class__.__name__.lower()), "user": collaborator}
            )
        if user_is_collaborator:
            raise learning.exc.UserIsAlreadyCollaborator(
                _("The user “%(user)s” already collaborates on this %(object)s. "
                  "Maybe you just want to change its role?")
                % {"object": _(self.__class__.__name__.lower()), "user": collaborator}
            )
        return self.object_collaborators.create(collaborator=collaborator, role=role.name)

    def remove_collaborator(self, collaborator: get_user_model()) -> None:
        """
        Remove a collaborator from the object

        :raises UserNotCollaboratorError: when the user is not a collaborator on the object

        :param collaborator: the collaborator to remove from the object
        :type collaborator: get_user_model()
        """
        user_is_collaborator = collaborator in self.collaborators.all()
        if not user_is_collaborator:
            raise learning.exc.UserNotCollaboratorError(
                _("The user “%(user)s” is not already a collaborator on this %(object)s.")
                % {"object": _(self.__class__.__name__.lower()), "user": collaborator}
            )
        self.object_collaborators.filter(collaborator=collaborator).delete()

    def change_collaborator_role(self, collaborator: get_user_model(), role: CollaboratorRole) -> None:
        """
        Change the role of a collaborator on the object

        :raises UserNotCollaboratorError: when the user is not a collaborator on the object

        :param collaborator: the collaborator for which to change his role
        :type collaborator: get_user_model()
        :param role: the new role for the collaborator
        :type role: CollaboratorRole
        """
        user_is_collaborator = collaborator in self.collaborators.all()
        if not user_is_collaborator:
            raise learning.exc.UserNotCollaboratorError(
                _("The user “%(user)s” does not collaborates on this %(object)s. "
                  "Maybe you just want to add it as a collaborator?")
                % {"object": _(self.__class__.__name__.lower()), "user": collaborator}
            )
        self.object_collaborators.filter(collaborator=collaborator).update(role=role.name)

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        permissions = set()
        if user == self.author:
            permissions.update([
                # Basic CRUD actions
                "view", "delete", "add", "change",
                # Extra access for objects
                "view_similar",
                # Collaborators permissions
                "add_collaborator", "delete_collaborator", "change_collaborator", "view_collaborators",
                # Objective permissions
                "add_objective", "view_objective", "delete_objective", "change_objective"
            ])
        return permissions

    def clean(self) -> None:
        """
        Check whether the model is clean or not.

        :return: True is the model is clean.
        """
        if self.language == str():
            raise ValidationError(_("No language selected."))

    def add_objective(self, objective: Objective, taxonomy_level: TaxonomyLevel, objective_reusable: bool) -> None:
        """
        Add a learning course_objective on the object.

        FIXME: why taxonomy level is not an attribute of Objective?

        :param objective: the course_objective to add on this object
        :type objective: Objective
        :param taxonomy_level: the taxonomy level the object is attached with
        :type taxonomy_level: TaxonomyLevel
        :param objective_reusable: whether the course_objective is reusable
        :type objective_reusable: bool
        """
        objective_already_in_model = objective in self.objectives.all()
        if objective_already_in_model:
            raise learning.exc.ObjectiveAlreadyInModel(
                _("The %(ability)s is already linked with this %(model_name)s.") %
                {"model_name": _(type(self).__name__.lower()), "ability": objective.ability})
        created_objective = self.object_objectives.create(
            objective=objective, taxonomy_level=taxonomy_level,objective_reusable=objective_reusable
        )
        if objective_reusable:
            for validator in objective.validators.all():
                created_objective.add_validator(validator)

    def remove_objective(self, objective: Objective) -> None:
        """
        Remove an course_objective from this entity.

        :param objective:
        :return:
        """
        objective_not_in_model = objective not in self.objectives.all()
        if objective_not_in_model:
            raise learning.exc.ObjectiveNotInModel(
                _("The %(ability)s is not linked with this entity %(model_name)s yet.")
                % {"model_name": _(type(self).__name__.lower()), "ability": objective.ability}
            )
        self.object_objectives.filter(objective=objective).delete()

    class Meta:
        abstract = True


def extract_all_included_objects(base_object: BasicModelMixin) -> Generator[BasicModelMixin, None, None]:
    """
    This generator return iteratively every included objects, whatever the depth is.

    :param base_object: the object that has included dependencies
    :type base_object: BasicModelMixin
    :return: a generator of included objects
    :rtype: Generator[BasicModelMixin, None, None]
    """
    for an_object in base_object.linked_objects:
        for linked_object in extract_all_included_objects(an_object):
            yield linked_object
        yield an_object


class ActivityAccess(OrderedEnum):
    """
    Defines the different access rights for activities.
    """
    PUBLIC = (_("Public"), 0)
    EXISTING_COURSES = (_("Only in courses"), 1)
    COLLABORATORS_ONLY = (_("Collaborators only"), 2)
    PRIVATE = (_("Private"), 3)


class ActivityReuse(OrderedEnum):
    """
    Defines the different reuse rights for resources.
    """
    NO_RESTRICTION = (_("Reusable"), 0)
    ONLY_AUTHOR = (_("Author only"), 1)
    NON_REUSABLE = (_("Non reusable"), 2)


class CourseState(Enum):
    """
    State of a course
    """
    DRAFT = _("Draft")
    PUBLISHED = _("Published")
    ARCHIVED = _("Archived")


class CourseAccess(OrderedEnum):
    """
    Access permissions on a course
    """
    PUBLIC = (_("Public"), 0)
    STUDENTS_ONLY = (_("Students only"), 1)
    COLLABORATORS_ONLY = (_("Collaborators only"), 2)
    PRIVATE = (_("Private"), 3)


class ResourceManager(BasicModelManager):
    """
    The resource specific Model Manager
    """

    # noinspection PyMissingOrEmptyDocstring
    def public(self, **kwargs) -> QuerySet:
        return self._filter_with_query(
            super().get_queryset().filter(access=ResourceAccess.PUBLIC.name), kwargs.get("query", "")
        )

    def recommendations_for(self, user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all resources opened for registration and recommended for a user

        .. note:: A recommendation concerns resources the user is not registered as a \
        student or as a teacher and is public and published.

        :param user: the user for which to query recommendations
        :type user: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: Resources recommended for the user
        :rtype: QuerySet
        """
        qs = super().get_queryset() \
            .exclude(Q(author=user) | Q(collaborators=user)) \
            .filter(Q(reuse=ResourceReuse.NO_RESTRICTION.name) & Q(access=ResourceAccess.PUBLIC.name))
        return self._filter_with_query(qs, kwargs.get("query", ""))

    def reusable(self, activity: "Activity", user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all the reusable resources for a specific activity.

        :param activity: The Activity for which to search reusable resources.
        :type activity: Activity
        :param user: the user for which resources should be reusable
        :type user: get_user_model()
        :return: a queryset of reusable resources
        :rtype QuerySet
        """
        qs = super().get_queryset().exclude(
            activities=activity
        ).exclude(
            reuse=ResourceReuse.NON_REUSABLE.name
        ).exclude(
            Q(reuse=ResourceReuse.ONLY_AUTHOR.name) & ~Q(author=user)
            # Resources that can be reused by their author
        )
        return self._filter_with_query(qs, kwargs.get("query", ""))


def resource_attachment_upload_to_callback(resource: 'Resource', filename: str):
    """
    Set the upload filename.

    :param resource:
    :type: Resource
    :param filename:
    :return: str
    """
    return "resources/{resource_id}/{filename}".format(resource_id=resource.id, filename=filename)


class Resource(BasicModelMixin):
    """
    The resource object: this object may contained an attached resource which include educative material.
    """
    type = models.CharField(
        max_length=10,
        choices=[(rtype.name, rtype.value) for rtype in ResourceType],
        verbose_name=_("Type"),
        help_text=_("Whether this resource is a common file, a video file or an audio")
    )
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="resources",
        verbose_name=_("Author"),
        help_text=_("The user that created this resource, or that is considered as the current owner")

    )
    collaborators = models.ManyToManyField(
        get_user_model(),
        through="ResourceCollaborator",
        related_name="collaborates_on_resource",
        verbose_name=_("Collaborators"),
        help_text=_("The users that collaborate on this resource alongside the author")
    )
    duration = models.CharField(
        max_length=30,
        choices=[(duration.name, duration.value) for duration in Duration],
        default=Duration.NOT_SPECIFIED.name,
        verbose_name=_("Duration"),
        help_text=_("The estimated, required duration to consult and understand the resource")
    )
    licence = models.CharField(
        max_length=20,
        choices=[(licence.name, licence.value) for licence in Licences],
        default=Licences.CC_BY.name,
        verbose_name=_("Licence"),
        help_text=_(
            "The licence under which the content is provided. If you want to share your work with the community"
            "a Creative Commons Licence is a bit more adapted. Anyway you can choose to keep your rights on "
            "your resource")
    )
    access = models.CharField(
        max_length=20,
        choices=[(access.name, access.value) for access in ResourceAccess],
        default=ResourceAccess.PUBLIC.name,
        verbose_name=_("Access"),
        help_text=_("Whether the resource should remain private (for you only), visible only in activities that use it"
                    ", restricted to your collaborators or public")
    )
    reuse = models.CharField(
        max_length=20,
        choices=[(reuse.name, reuse.value) for reuse in ResourceReuse],
        default=ResourceReuse.ONLY_AUTHOR.name,
        verbose_name=_("Reuse"),
        help_text=_("Whether you want the resource to be reusable in an activity created by other users."
                    " Resources can be fully reusable, only by you or not reusable")
    )
    attachment = models.FileField(
        blank=True, null=True,
        verbose_name=_("File"),
        upload_to=resource_attachment_upload_to_callback
    )
    objectives = models.ManyToManyField(
        Objective,
        through="ResourceObjective",
        related_name="objectives_on_resource",
        verbose_name=_("Objectives"),
        help_text=_("The objectives that are in the resource")
    )

    # noinspection PyMissingOrEmptyDocstring
    class PermissionMessage(Enum):
        VIEW = _("Can view the resource")
        CHANGE = _("Can change the resource")
        DELETE = _("Can delete the resource")

    objects = ResourceManager()

    @property
    def object_collaborators(self) -> QuerySet:
        """
        Get the resource collaborators

        :return: the resource collaborators
        :rtype: QuerySet
        """
        return self.resource_collaborators

    @property
    def object_objectives(self):
        return self.resource_objectives

    @property
    def linked_objects(self) -> None:
        """
        A resource does not have any linked object.
        :return: None
        """
        yield

    def is_reusable(self, for_activity=None) -> bool:
        """
        Check if it is possible to use the resource in an activity. Resource linking depends on a few conditions, based on
        access and reuse Resource attributes.

        :raises ResourceNotReusableError: when reuse condition do not allow the Resource to be reused by any Activity
        :raises ResourceNotReusableOnlyAuthorError: when reuse condition is set to “Only author” and the Resource \
            author and the author of the activity given in parameter do not match.
        :raises RuntimeError: when reuse condition is set to “Only author” but no activity is given in parameter

        :param for_activity: in case the reuse attribute is set to “Only author”, this argument must be provided. \
            It indicates for which activity to link the resource.
        :type for_activity: Activity
        :return: True if reusing resource is possible
        :rtype: bool
        """
        reuse = ResourceReuse[self.reuse]
        # Reuse is stricter than “Only Author”, means no one has access
        if reuse > ResourceReuse.ONLY_AUTHOR:
            raise learning.exc.ResourceNotReusableError(
                _("Reuse conditions for this resource prevent it from being added to an activity."))
        if reuse == ResourceReuse.ONLY_AUTHOR:
            if for_activity is None:
                raise RuntimeError(
                    "If resource reuse condition is set to “Only author”, you must provide the corresponding activity.")
            if reuse == ActivityReuse.ONLY_AUTHOR and for_activity.author != self.author:
                raise learning.exc.ResourceNotReusableOnlyAuthorError(
                    _("The author of this resource is the only one allowed to add it an activity that it owns.")
                )
        return True

    @staticmethod
    def acceptable_media(attachment: models.FileField) -> bool:
        """
        Check whether the attachment file given is acceptable for this resource. This includes checking the file size
        and any other relevant constraint.

        :param attachment: the FileField to check
        :type: models.FileField
        :return: True is the attachment is acceptable and can be used.
        :rtype: bool
        """
        # noinspection PyUnresolvedReferences
        return attachment and attachment.size <= get_max_upload_size()

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        super().clean()
        # Check the attachment upload size
        if self.attachment and not Resource.acceptable_media(self.attachment):
            raise ValidationError(
                _("The file you tried to upload to the application is too big: you sent %(attachment_size)s "
                  "(maximum is %(upload_size)s).")
                % {
                    "attachment_size": filesizeformat(self.attachment.size),
                    "upload_size": filesizeformat(get_max_upload_size())
                }
            )

        # Check resource access
        if self.access == ResourceAccess.PRIVATE.name and self.reuse == ResourceReuse.NO_RESTRICTION.name:
            raise ValidationError(_("The resource is private but also reusable. This is inconsistent."))

        # Check resource licence
        if Licences[self.licence] > Licences.CC_BY_NC_ND and self.reuse == ResourceReuse.NO_RESTRICTION.name:
            raise ValidationError(
                _("The resource can be reused by anyone but the licence is too restrictive. Choose a "
                  "Creative Commons licence if you wish to share your content."))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        save() method is overridden to generate the slug field.
        """
        self.slug = generate_slug_for_model(Resource, self)

        # This code ensures that it is possible to use resource id in the upload_to function
        if not self.id and self.attachment:
            saved_attachment = self.attachment
            self.attachment = None
            super().save(force_insert, force_update, using, update_fields)
            self.attachment = saved_attachment  # calling save(…) once again will allow upload_to to know id

        super().save(force_insert, force_update, using, update_fields)

    def delete(self, using=None, keep_parents=False):
        """
        delete() method is overridden to ensure the associated file is deleted at \
        the same time as the object.
        """
        if self.attachment:
            try:
                os.remove(os.path.join(settings.MEDIA_ROOT, self.attachment.name))
            except OSError as ex:
                logger.error(
                    "Deleting attachment for resource %(resource)s failed (%(cause)s)", resource=self, cause=str(ex)
                )
        return super().delete()

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        permissions = super()._get_user_perms(user)
        if self.author == user:
            permissions.update(["view_usage", "toggle_important_question"])
        if self.access == ResourceAccess.PUBLIC.name:
            permissions.update(["view"])
        if self.access == ResourceAccess.EXISTING_ACTIVITIES.name:
            activities_with_this_resource = Activity.objects.filter(resources=self).all()
            for activity in activities_with_this_resource:
                # If able to see one of the linked course, it’s ok to view the activity
                if "view_activity" in activity.get_user_perms(user):
                    permissions.update(["view"])
                    break
        if user in self.collaborators.all() and ResourceAccess[self.access] <= ResourceAccess.COLLABORATORS_ONLY:
            permissions.update(PERMISSIONS_FOR_ROLE.get(self.object_collaborators.get(collaborator=user).role, set()))
        return permissions

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-updated", "name"]
        verbose_name = pgettext_lazy("Resource verbose name (singular form)", "resource")
        verbose_name_plural = pgettext_lazy("Resource verbose name (plural form)", "resources")


class ActivityManager(BasicModelManager):
    """
    The activity specific Model Manager
    """

    # noinspection PyMissingOrEmptyDocstring
    def public(self, **kwargs) -> QuerySet:
        return self._filter_with_query(
            super().get_queryset().filter(access=ActivityAccess.PUBLIC.name), kwargs.get("query", "")
        )

    def recommendations_for(self, user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all activities opened for registration and recommended for a user

        .. note:: A recommendation concerns activities the user is not registered as a \
        student or as a teacher and is public and published.

        :param user: the user for which to query recommendations
        :type user: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: Activities recommended for the user
        :rtype: QuerySet
        """
        qs = super().get_queryset() \
            .exclude(Q(students=user) | Q(author=user) | Q(collaborators=user)) \
            .filter(Q(state=ActivityReuse.NO_RESTRICTION.name) & Q(access=ActivityAccess.PUBLIC.name))
        return self._filter_with_query(qs, kwargs.get("query", ""))

    def reusable(self, course: "Course", user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all the reusable activities for a specific course.

        # FIXME: what is the author of the course is also the author of the activity. Is it excluded?

        :param course: The Course for which to search reusable activities.
        :type course: Course
        :param user: the user for which resources should be reusable
        :type user: get_user_model()
        :return: a queryset of reusable activities
        :rtype QuerySet
        """
        qs = super().get_queryset().exclude(
            # activities already linked with the course
            course_activities__course=course
        ).exclude(
            # activities that are not reusable
            reuse=ActivityReuse.NON_REUSABLE.name,
        ).exclude(
            # activities that can only be reused by their respective authors
            Q(reuse=ActivityReuse.ONLY_AUTHOR.name) & ~Q(author=user)
        )
        return self._filter_with_query(qs, kwargs.get("query", ""))


class Activity(BasicModelMixin):
    """
    The activity object: it is aggregated in courses and aggregates resources.
    """
    access = models.CharField(
        max_length=20,
        choices=[(access.name, access.value) for access in ActivityAccess],
        default=ActivityAccess.PUBLIC.name,
        verbose_name=_("Access"),
        help_text=_("Whether the activity should remain private (for you only), visible only in courses that use it, "
                    "restricted to your collaborators or public")
    )
    reuse = models.CharField(
        max_length=20,
        choices=[(reuse.name, reuse.value) for reuse in ActivityReuse],
        default=ActivityReuse.ONLY_AUTHOR.name,
        verbose_name=_("Reuse"),
        help_text=_(
            "Whether you want the activity to be reusable in courses made by other users."
            " Activities can be fully reusable, only by you or not reusable")
    )
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name=_("Author"),
        help_text=_("The user that created this activity, or that is considered as the current owner")
    )
    collaborators = models.ManyToManyField(
        get_user_model(),
        through="ActivityCollaborator",
        related_name="collaborates_on_activity",
        verbose_name=_("Collaborators"),
        help_text=_("The users that collaborate on this activity alongside the author")
    )
    resources = models.ManyToManyField(Resource, related_name="activities", verbose_name=_("Resources"))

    objectives = models.ManyToManyField(
        Objective,
        through="ActivityObjective",
        related_name="objectives_on_activity",
        verbose_name=_("Objectives"),
        help_text=_("The objectives that are in the activity")
    )

    # noinspection PyMissingOrEmptyDocstring
    class PermissionMessage(Enum):
        VIEW = _("Can view the activity")
        CHANGE = _("Can change the activity")
        DELETE = _("Can delete the activity")

    objects = ActivityManager()

    @property
    def object_collaborators(self) -> QuerySet:
        """
        Get the activity collaborators

        :return: the activity collaborators
        :rtype: QuerySet
        """
        return self.activity_collaborators

    @property
    def object_objectives(self):
        return self.activity_objectives

    @property
    def linked_objects(self) -> Generator[Resource, None, None]:
        """
        The included resources for this activity. This means all the resources aggregated by this activity.

        :return: The Generator that references the included objects
        :rtype: Generator
        """
        return Resource.objects.filter(activities=self).all()

    def is_reusable(self, for_course=None) -> bool:
        """
        Check if it is possible to use the activity in a course. Activity linking depends on a few conditions, based \
            on access and reuse Activity attributes.

        :raises ActivityNotReusableError: when reuse condition do not allow the activity to be reused by any course
        :raises ActivityNotReusableOnlyAuthorError: when reuse condition is set to “Only author” and the activity \
            author and the author of the course given in parameter do not match.
        :raises RuntimeError: when reuse condition is set to “Only author” but no course is given in parameter

        :param for_course: in case the reuse attribute is set to “Only author”, this argument must be provided. \
            It indicates for which course to link the activity.
        :type for_course: Course
        :return: True if reusing activity is possible
        :rtype: bool
        """
        reuse = ActivityReuse[self.reuse]
        # Reuse is stricter than “Only Author”, means no one has access
        if reuse > ActivityReuse.ONLY_AUTHOR:
            raise learning.exc.ActivityNotReusableError(
                _("Reuse conditions for this activity prevent it from being added to a course."))
        if reuse == ActivityReuse.ONLY_AUTHOR:
            if for_course is None:
                raise RuntimeError(
                    "If activity reuse condition is set to “Only author”, you must provide the corresponding course.")
            if reuse == ActivityReuse.ONLY_AUTHOR and for_course.author != self.author:
                raise learning.exc.ActivityNotReusableOnlyAuthorError(
                    _("The author of this activity is the only one allowed to add it a course that it owns.")
                )
        return True

    def add_resource(self, resource: Resource):
        """
        Add a resource on an activity.

        .. note:: You do not need to save the resource before calling this method. It the resource can be added, it will
         be saved anyway.

        :raises ResourceAlreadyOnActivityError: when the Resource is already linked with the Activity
        :raises ResourceNotReusableError: when reuse condition do not allow the Resource to be reused by any Activity
        :raises ResourceNotReusableOnlyAuthorError: when reuse condition is set to “Only author” and the Resource \
            author and the author of the activity given in parameter do not match.

        :param resource: the resource to add on the activity
        :type resource: Resource
        """
        if resource in self.resources.all():
            raise learning.exc.ResourceAlreadyOnActivityError(
                _("%(resource)s is already linked with this activity. Operation cancelled.") % {"resource": resource}
            )
        if resource.is_reusable(for_activity=self):
            resource.save()
            self.resources.add(resource)

    def remove_resource(self, resource: Resource):
        """
        Remove the resource from the activity. This means the link between the resource and the activity is removed.

        :raises ResourceIsNotLinkedWithThisActivityError: when the resource is not already linked with the activity

        :param resource: the resource to remove from the activity
        :type resource: Resource
        """
        if resource not in self.resources.all():
            raise learning.exc.ResourceIsNotLinkedWithThisActivityError(
                _("%(resource)s is not linked with this activity. Hence, it cannot be removed from the activity.") % {
                    "resource": resource}
            )
        self.resources.remove(resource)

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        super().clean()
        if self.access == ActivityAccess.PRIVATE.name and self.reuse == ActivityReuse.NO_RESTRICTION.name:
            raise ValidationError(
                _("The activity is private and also reusable. This is inconsistent. "
                  "If you wish to share the activity, it should be visible by users.")
            )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        save() method is overridden to generate the slug field.
        """
        self.slug = generate_slug_for_model(Activity, self)
        super().save(force_insert, force_update, using, update_fields)

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        permissions = super()._get_user_perms(user)
        if self.author == user:
            permissions.update(["view_usage", "toggle_important_question"])
        if self.access == ActivityAccess.PUBLIC.name:
            permissions.update(["view"])
        if self.access == ActivityAccess.EXISTING_COURSES.name:
            courses_with_this_activity = Course.objects.filter(course_activities__activity=self).all()
            for course in courses_with_this_activity:
                # If able to see one of the linked course, it’s ok to view the activity
                if "view_course" in course.get_user_perms(user):
                    permissions.update(["view"])
                    break
        if user in self.collaborators.all() and ActivityAccess[self.access] <= ActivityAccess.COLLABORATORS_ONLY:
            permissions.update(PERMISSIONS_FOR_ROLE.get(self.object_collaborators.get(collaborator=user).role, set()))
        return permissions

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-updated", "name"]
        verbose_name = pgettext_lazy("Activity verbose name (singular form)", "activity")
        verbose_name_plural = pgettext_lazy("Activity verbose name (plural form)", "activities")


class CourseManager(BasicModelManager):
    """
    The Course specific Model Manager.
    """

    # noinspection PyMissingOrEmptyDocstring
    def public(self, **kwargs) -> QuerySet:
        return self._filter_with_query(
            super().get_queryset().filter(access=CourseAccess.PUBLIC.name), kwargs.get("query", "")
        )

    # noinspection PyMissingOrEmptyDocstring
    def public_without_followed_by_without_taught_by(self, student: get_user_model(), teacher: get_user_model(),
                                                     **kwargs) -> QuerySet:
        return self._filter_with_query(
            super().get_queryset().filter(access=CourseAccess.PUBLIC.name).exclude(students=student).exclude(
                Q(author=teacher) | Q(collaborators=teacher)), kwargs.get("query", "")
        )

    def recommendations_for(self, user: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all courses opened for registration and recommended for a user

        .. note:: A recommendation concerns courses the user is not registered as a \
        student or as a teacher and is public and published.

        :param user: the user for which to query recommendations
        :type user: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: Courses recommended for the user
        :rtype: QuerySet
        """
        qs = super().get_queryset() \
            .exclude(Q(students=user) | Q(author=user) | Q(collaborators=user)) \
            .filter(Q(state=CourseState.PUBLISHED.name) & Q(access=CourseAccess.PUBLIC.name))
        return self._filter_with_query(qs, kwargs.get("query", ""))

    def followed_by(self, student: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all courses followed by the student

        :param student: a user that is registered in courses
        :type: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: all courses followed by the student
        :rtype: QuerySet
        """
        return self._filter_with_query(super().get_queryset().filter(students=student), kwargs.get("query", ""))

    def followed_by_without_favorites(self, student: get_user_model(), **kwargs) -> QuerySet:
        """
        Get all courses except the favorites followed by the student

        :param student: a user that is registered in courses
        :type: get_user_model()
        :param kwargs: kwargs that can contain a key “query” to filter name and description
        :type kwargs: dict
        :return: all courses followed by the student
        :rtype: QuerySet
        """
        return self._filter_with_query(super().get_queryset().filter(students=student).exclude(favourite_for=student),
                                       kwargs.get("query", ""))


class Course(BasicModelMixin):
    """
    The course, that contains activities, which are course “chapters”.
    """

    state = models.CharField(
        max_length=20,
        choices=[(state.name, state.value) for state in CourseState],
        default=CourseState.DRAFT.name,
        verbose_name=_("State"),
        help_text=_("Whether the course should be considered as a draft, published or archived. Archived means "
                    "read-only."),
        blank=False,
        null=False
    )
    access = models.CharField(
        max_length=20,
        choices=[(access.name, access.value) for access in CourseAccess],
        default=CourseAccess.PUBLIC.name,
        verbose_name=_("Access"),
        help_text=_("Whether the course should remain private (for you only), restricted to your collaborators, "
                    "your students or public"),
        blank=False,
        null=False
    )
    registration_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Registration enabled"),
        help_text=_("Whether users are authorised to register or unregister from this course")
    )
    author = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="courses",
        verbose_name=_("Author"),
        help_text=_("The user that created this course, or that is considered as the current owner")
    )
    collaborators = models.ManyToManyField(
        get_user_model(),
        through="CourseCollaborator",
        related_name="collaborates_on_course",
        verbose_name=_("Collaborators"),
        help_text=_("The users that collaborate on this course alongside the author")
    )
    students = models.ManyToManyField(
        get_user_model(),
        through="RegistrationOnCourse",
        related_name="registered_on",
        verbose_name=_("Students"),
        help_text=_("The users that registered on this course, that are hence considered as students")
    )

    # noinspection PyMissingOrEmptyDocstring
    class PermissionMessage(Enum):
        VIEW = _("Can view the course")
        CHANGE = _("Can change the course")
        DELETE = _("Can delete the course")

    objects = CourseManager()

    objectives = models.ManyToManyField(
        Objective,
        through="CourseObjective",
        related_name="objectives_on_course",
        verbose_name=_("Objectives"),
        help_text=_("The objectives that are in this course")
    )

    @property
    def object_collaborators(self):
        """
        Get the activity collaborators

        :return: the activity collaborators
        :rtype: QuerySet
        """
        return self.course_collaborators

    @property
    def object_objectives(self):
        return self.course_objectives

    @property
    def linked_objects(self) -> Generator[Activity, None, None]:
        """
        The included resources for this course. This means all the activities aggregated by this course.

        :return: The Generator that references the included objects
        :rtype: Generator
        """
        return Activity.objects.filter(course_activities__course=self).all()

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        super().clean()
        if self.id:
            if self.author in self.students.all():
                raise ValidationError(
                    _("%(user)s is already the author of the course. The user %(user)s cannot be added as a "
                      "student.") % {"user": self.author}
                )
            if self.author in self.collaborators.all():
                raise ValidationError(
                    _("%(user)s is already the author of the course. The user %(user)s cannot be added as a "
                      "collaborator.") % {"user": self.author}
                )
        if self.registration_enabled and \
            (self.state == CourseState.ARCHIVED.name or self.state == CourseState.DRAFT.name):
            raise ValidationError(
                _("You cannot enable registration on a course that is %(state)s.") % {
                    "state": CourseState[self.state].value}
            )
        if CourseAccess[self.access] >= CourseAccess.COLLABORATORS_ONLY and \
            CourseState[self.state] == CourseState.PUBLISHED:
            raise ValidationError(
                _("Access is collaborators only but course is published. It seems inconsistent. "
                  "If you wish to publish the course, you should at least let it accessible to students.")
            )

    @property
    def can_register(self) -> bool:
        """
        Indicates if it is possible to register on the course.

        :return: True if registration is possible
        :rtype: bool
        """
        return self.registration_enabled and CourseState[self.state] == CourseState.PUBLISHED

    def __check_student_registration(self, user: get_user_model()) -> bool:
        """
        Check is the user given in parameter can be added as a student on the course.
        Being a student on a course implies you’re not already a collaborator, you’re not the author of the course
        and you’re not already a student.

        :raises learning.exc.UserIsAlreadyCollaborator: when the user is a collaborator on the course
        :raises learning.exc.UserIsAlreadyAuthor when: the user is the author of the course
        :raises UserIsAlreadyStudent when: the user is already a student

        :param user: the user that is to be added as a student
        :type user: get_user_model()
        :return: True if registration is possible
        :rtype bool
        """
        user_is_collaborator = user in self.collaborators.all()
        user_is_author = user == self.author
        user_is_student = user in self.students.all()
        if user_is_collaborator:
            raise learning.exc.UserIsAlreadyCollaborator(
                _("%(user)s cannot register on this course. %(user)s is already "
                  "a collaborator on this course, a user cannot be both.") % {"user": user}
            )
        if user_is_author:
            raise learning.exc.UserIsAlreadyAuthor(
                _("%(user)s is already the author of this course. %(user)s cannot "
                  "register as a student.") % {"user": user}
            )
        if user_is_student:
            raise learning.exc.UserIsAlreadyStudent(
                _("%(user)s is already registered on this course.") % {"user": user}
            )
        return True

    def register(self, student: get_user_model()):
        """
        Register, as a student, on the course.

        :raises RegistrationDisabledError: when registration is disabled on the course
        :raises UserIsAlreadyCollaborator: when the user is a collaborator on the course
        :raises UserIsAlreadyAuthor: when the user is the author of the course
        :raises UserIsAlreadyStudent: when the user is already a student

        :param student: The student that wants to register on the course.
        :type student: get_user_model()
        """
        if not self.can_register:
            raise learning.exc.RegistrationDisabledError(
                _("Nobody can register on this course. Registration is disabled or the course is not published yet.")
            )
        if self.__check_student_registration(student):
            # noinspection PyUnresolvedReferences
            self.registrations.create(student=student, self_registration=True)

    def register_student(self, student: get_user_model(), registration_locked=True):
        """
        Register a student on the course

        :raises UserIsAlreadyCollaborator: when the user is a collaborator on the course
        :raises UserIsAlreadyAuthor: when the user is the author of the course
        :raises UserIsAlreadyStudent: when the user is already a student

        :param student: The student will be registered on the course.
        :type student: get_user_model()
        :param registration_locked: Indicates whether the registration is locked, meaning the user
                                    cannot self-unregister.
        :type registration_locked: bool
        """
        if self.__check_student_registration(student):
            # noinspection PyUnresolvedReferences
            self.registrations.create(student=student, registration_locked=registration_locked)

    def __check_student_unsubscription(self, user: get_user_model()) -> bool:
        """
        Check is the user given in parameter can be removed from students of this course.
        Unsubscription is possible when registration is not disabled and when the user is already a student on this
        course.

        :raises UserIsNotStudent: when the user to unsubscribe is not a student

        :param user: the user that is to be added as a student
        :type user: get_user_model()
        :return: True if registration is possible
        :rtype bool
        """
        user_is_student = user in self.students.all()
        if not user_is_student:
            raise learning.exc.UserIsNotStudent(
                _("User “%(user)s is not a student registered on this course. Thus %(user)s cannot be unregistered.")
                % {"user": user}
            )
        return user_is_student

    def unsubscribe(self, student: get_user_model()):
        """
        Unsubscribe, as a student, from the course

        :raises RegistrationDisabledError: when registration is disabled on the course
        :raises UserIsNotStudent: when the user to unsubscribe is not a student

        :param student: The student that wants to unsubscribe from the course.
        :type student: get_user_model()
        """
        if not self.can_register:
            raise learning.exc.RegistrationDisabledError(
                _("Nobody can unregister from this course. Registration is disabled or the course is no longer "
                  "published.")
            )
        if student in self.students.all() and self.registrations.get(student=student).registration_locked:
            raise learning.exc.RegistrationDisabledError(
                _("You cannot unregister from this course. Registration is locked for you.")
            )
        if self.__check_student_unsubscription(student):
            # noinspection PyUnresolvedReferences
            self.registrations.get(student=student).delete()

    def unsubscribe_student(self, user: get_user_model()):
        """
        Unsubscribe a student from the course

        :raises UserIsNotStudent: when the user to unsubscribe is not a student

        :param user:The student that has to be unsubscribed from the course.
        :type user: get_user_model()
        """
        if self.__check_student_unsubscription(user):
            # noinspection PyUnresolvedReferences
            self.registrations.get(student=user).delete()

    def add_collaborator(self, collaborator: get_user_model(), role: CollaboratorRole):
        """
        Add a collaborator on a course.

        :raises UserIsAlreadyAuthor: when the user is already the author of the course
        :raises UserIsAlreadyCollaborator: when the user is already a collaborator on the course
        :raises UserIsAlreadyStudent: when the user is already a student

        :param collaborator: the collaborator to add on the course
        :type collaborator: get_user_model()
        :param role: the role of the collaborator on the course
        :type role: CollaboratorRole
        """
        user_is_student = collaborator in self.students.all()
        if user_is_student:
            raise learning.exc.UserIsAlreadyStudent(
                _("%(user)s is already registered on this course.") % {"user": collaborator}
            )
        super().add_collaborator(collaborator=collaborator, role=role)

    @property
    def activities(self) -> Generator["Activity", None, None]:
        """
        Get activities of this course, sorted by their rank.

        :return: the Generator of Activity objects linked to this course.
        :rtype: Generator of CourseActivity
        """
        for course_activity in self.course_activities.all():
            yield course_activity.activity

    def reorder_course_activities(self):
        """
        Reorder the course activities, this means updating the “rank” field in order to ensure consistency.
        """
        ranked_activities = self.course_activities.all()

        # Check if course activities are ordered correctly
        in_order, rank_counter = True, 1
        for ranked_course_activity in ranked_activities:
            if not in_order:
                break
            if not ranked_course_activity.rank == rank_counter:
                in_order = False
            else:
                rank_counter += 1

        # If not, reorder them manually
        if not in_order:
            new_rank = 1
            for course_activity in ranked_activities:
                course_activity.rank = new_rank
                course_activity.save()
                new_rank += 1

    def add_activity(self, activity):
        """
        Add an activity on this course.

        .. note:: You do not need to save the activity before calling this method. It the resource can be added, it will
         be saved anyway.

        :raises ChangeActivityOnCourseError: when changing activity on the course is not possible
        :raises ActivityAlreadyOnCourseError: when activity is already linked with the course
        :raises ActivityNotReusableError: when reuse condition do not allow the resource to be reused by any activity
        :raises ActivityNotReusableOnlyAuthorError: when reuse condition is set to “Only author” and the activity \
            author and the author of the course do not match.

        :param activity: the activity to add on the course
        :type activity: Activity
        """
        if self.read_only:
            raise learning.exc.ChangeActivityOnCourseError(
                _("This course is read only. It is not possible to add activities."))
        if activity in self.activities:
            raise learning.exc.ActivityAlreadyOnCourseError(
                _("“%(activity)s is already linked with this course. Operation cancelled.")
                % {"activity": activity}
            )
        if activity.is_reusable(for_course=self):
            # TODO: rewrite this block. This is not well written and understanding is quite hard
            last_rank = CourseActivity.objects.filter(course=self).aggregate(Max("rank")).get("rank__max", 0)
            activity.save()
            CourseActivity.objects.create(
                course=self, activity=activity, rank=1 if last_rank is None else last_rank + 1
            )
            self.reorder_course_activities()

    def remove_activity(self, activity: Activity):
        """
        Remove the activity from the course. This means the link between the activity and the course is removed.

        :raises ChangeActivityOnCourseError: when changing activity on the course is not possible
        :raises ActivityIsNotLinkedWithThisCourseError: when activity is not linked with the course yet

        :param activity: the activity to remove on this course
        :type activity: Activity
        """
        if self.read_only:
            raise learning.exc.ChangeActivityOnCourseError(
                _("This course is read only. It is not possible to remove activities."))
        if activity not in self.activities:
            raise learning.exc.ActivityIsNotLinkedWithThisCourseError(
                _("“%(activity)s is not linked with this course. Hence, it cannot be removed from the course.")
                % {"activity": activity}
            )
        CourseActivity.objects.filter(course=self, activity=activity).get().delete()
        self.reorder_course_activities()

    @property
    def read_only(self) -> bool:
        """
        Indicates whether the course is read only or not

        :return: True if the course a read-only
        :rtype: bool
        """
        return CourseState[self.state] == CourseState.ARCHIVED

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        save() method is overridden to generate the slug field.
        """
        self.slug = generate_slug_for_model(Course, self)
        super().save(force_insert, force_update, using, update_fields)

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        permissions = super()._get_user_perms(user)
        # Public access means everyone can view it
        if self.access == CourseAccess.PUBLIC.name:
            permissions.update(["view"])
        # Being author of a course implies you have the owner permissions
        if user == self.author:
            permissions.update(PERMISSIONS_FOR_ROLE.get(CollaboratorRole.OWNER.name, set()))
        # Being a student with students only access or lower implies you have the students permissions
        if user in self.students.all() and CourseAccess[self.access] <= CourseAccess.STUDENTS_ONLY:
            permissions.update(PERMISSIONS_FOR_ROLE.get("students", set()))
        # Being a collaborator with collaborators only access or lower implies you have the collaborators permissions
        if user in self.collaborators.all() and CourseAccess[self.access] <= CourseAccess.COLLABORATORS_ONLY:
            permissions.update(PERMISSIONS_FOR_ROLE.get(self.object_collaborators.get(collaborator=user).role, set()))
        return permissions

    def get_all_objectives(self) -> set:
        """
        This method return all the objectives which are attached to the courses. This include:
        Course objectives
        Course activities objectives
        Course activities resources objectives
        This method is used for the progression
        :return: set() which contains all the Objective (object) in the course
        A set is used because it needs to remove occurrences
        """
        all_objectives_in_the_course = set()
        for objective in self.objectives.all():
            all_objectives_in_the_course.add(objective)
        for course_activity in self.activities:
            for objective in course_activity.objectives.all():
                all_objectives_in_the_course.add(objective)
            for activity_resource in course_activity.resources.all():
                for objective in activity_resource.objectives.all():
                    all_objectives_in_the_course.add(objective)

        return all_objectives_in_the_course

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-updated", "name"]
        verbose_name = pgettext_lazy("Course verbose name (singular form)", "course")
        verbose_name_plural = pgettext_lazy("Course verbose name (plural form)", "courses")


class CourseActivity(models.Model):
    rank = models.PositiveIntegerField(verbose_name=_("Rank"))
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_activities",
        verbose_name=_("Course")
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="course_activities",
        verbose_name=_("Activity")
    )

    def __str__(self):
        return _("“%(activity)s”, n°%(rank)d on “%(course)s”") % {"activity": self.activity, "rank": self.rank,
                                                                  "course": self.course}

    class Meta:
        unique_together = ("activity", "course")
        ordering = ["rank"]
        verbose_name = pgettext_lazy("Course activity verbose name (singular form)", "course activity")
        verbose_name_plural = pgettext_lazy("Course activity verbose name (plural form)", "course activities")


class RegistrationOnCourse(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        verbose_name=_("Course"),
        related_name="registrations"
    )
    student = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        verbose_name=_("Student"),
        related_name="registrations"
    )
    self_registration = models.BooleanField(
        default=False,
        verbose_name=_("User registered by itself"),
        help_text=_("Indicates the user decided to register to the course by itself, the user was not registered "
                    "manually by a teacher in the course or as a member of a group.")
    )
    registration_locked = models.BooleanField(
        default=False,
        verbose_name=_("Registration locked"),
        help_text=_("Locking a registration means the user will not be able to unregister by itself.")
    )

    """
    Auto-generated fields
    """
    # noinspection PyArgumentEqualDefault
    created = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Registered the"))
    # noinspection PyArgumentEqualDefault
    updated = models.DateTimeField(auto_now_add=False, auto_now=True, verbose_name=_("Last updated the"))

    def __str__(self):
        return _("%(student)s, student in course “%(course)s”") % {
            "student": self.student,
            "course": self.course
        }

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        if self.course.author == self.student:
            raise ValidationError(
                _("%(user)s is already the author of this course. %(user)s cannot be "
                  "registered as a student.") % {"user": self.student}
            )
        if self.student in self.course.collaborators.all():
            raise ValidationError(
                _("%(user)s cannot register on this course. %(user)s is already "
                  "a collaborator on this course, a user cannot be both.") % {"user": self.student}
            )

    class Meta:
        ordering = ["course", "student"]
        unique_together = ("course", "student")
        verbose_name = pgettext_lazy("Course registration verbose name (singular form)", "course registration")
        verbose_name_plural = pgettext_lazy("Course registration verbose name (plural form)", "course registrations")


def add_validator_object_objective(student: get_user_model(), objective: Objective):
    """
    This method add the validation on course_objective for the EntityObjectives with validation reusable
    :param student: The student that you want to add validation
    :param objective: The course_objective concerned
    :return:
    """
    # Add the student in course_objective student  if this is his first course_objective validation (Objective class)
    if student not in objective.validators.all():
        objective.add_validator(student)
    # Update all ObjectObjective student list
    for course_objective in CourseObjective.objects.filter(objective=objective, objective_reusable=True):
        if student not in course_objective.validators.all():
            course_objective.add_validator(student)
    for activity_objective in ActivityObjective.objects.filter(objective=objective, objective_reusable=True):
        if student not in activity_objective.validators.all():
            activity_objective.add_validator(student)
    for resource_objective in ResourceObjective.objects.filter(objective=objective, objective_reusable=True):
        if student not in resource_objective.validators.all():
            resource_objective.add_validator(student)


def remove_validator_object_objective(student: get_user_model(), objective: Objective):
    """
    This method remove the validation on course_objective for the EntityObjectives with validation reusable
    :param student: The student that you want to remove validation
    :param objective: The course_objective concerned
    :return:
    """
    # Remove the validation if validation is reusable
    for course_objective in CourseObjective.objects.filter(objective=objective, objective_reusable=True):
        if student in course_objective.validators.all():
            course_objective.remove_validator(student)
    for activity_objective in ActivityObjective.objects.filter(objective=objective, objective_reusable=True):
        if student in activity_objective.validators.all():
            activity_objective.remove_validator(student)
    for resource_objective in ResourceObjective.objects.filter(objective=objective, objective_reusable=True):
        if student in resource_objective.validators.all():
            resource_objective.remove_validator(student)

    # Remove the course_objective validation if no one object course_objective has been validated
    objective.remove_validator(student)


class EntityObjective(ObjectPermissionManagerMixin, models.Model):
    """
    This is an abstract class which will complete the association between an course_objective and a BasicModelMixin
    (Course,Activity,Resource)
    """
    taxonomy_level = models.CharField(
        max_length=20,
        default=TaxonomyLevel.KNOWLEDGE.value,
        choices=[(choice.name, choice.value) for choice in TaxonomyLevel],
        verbose_name=_("Classification level"),
        help_text=_("The taxonomy classification level.")
    )
    needs_test = models.BooleanField(
        default=False,
        verbose_name=_("Objective needs test"),
        help_text=_("Whether this course_objective needs a test in order to be validated.")
    )
    objective_reusable = models.BooleanField(
        default=True,
        verbose_name=_("Validation within another entity"),
        help_text=_("If enable, the objective cannot be validated within another entity"),
    )
    created = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Since the"), null=True)

    @property
    @abc.abstractmethod
    def object_validator(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def related_entity(self):
        raise NotImplementedError

    def change_validation(self, student: get_user_model()) -> None:
        """
        Toggle the validation status of this entity. If the entity course_objective is already validated, reverse the
        validation to not validated.

        :param student: the student for which the switch should be made
        :type student: get_user_model()
        """
        student_already_validated = student in self.validators.all()
        if student_already_validated:
            self.remove_validator(student)
            if self.objective_reusable:
                remove_validator_object_objective(student, self.objective)
        else:
            self.add_validator(student)
            if self.objective_reusable:
                add_validator_object_objective(student, self.objective)

    def add_validator(self, validator: get_user_model()):
        already_validate = validator in self.validators.all()
        if already_validate:
            raise learning.exc.ObjectiveAlreadyValidated()
        self.object_validator.create(student=validator)

    def remove_validator(self, validator: get_user_model()):
        already_validate = validator in self.validators.all()
        if not already_validate:
            raise learning.exc.ObjectiveNotValidated()
        self.object_validator.filter(student=validator).delete()

    class Meta:
        abstract = True


class ValidationOnObjectiveManager(models.Manager):
    pass


class CourseObjective(EntityObjective):
    """
    This object links an course_objective with a course
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name=_("course_objectives"),
        verbose_name=_("Objective")
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name=_("course_objectives"),
        verbose_name=_("Course")
    )
    validators = models.ManyToManyField(
        get_user_model(),
        through="CourseObjectiveValidator",
        related_name=_("course_objectives"),
        verbose_name=_("Validators"),
        blank=True,
        help_text=_("Student who validated the course_objective")
    )

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        return {"view_objective_course"}

    @property
    def object_validator(self) -> 'ObjectiveValidatorMixin':
        return self.course_objective_validator

    @property
    def related_entity(self) -> BasicModelMixin:
        return self.course


class ActivityObjective(EntityObjective):
    """
    This object links an course_objective with a activity
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name=_("activity_objectives"),
        verbose_name=_("Objective")
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name=_("activity_objectives"),
        verbose_name=_("Activity")
    )
    validators = models.ManyToManyField(
        get_user_model(),
        through="ActivityObjectiveValidator",
        related_name=_("activity_objectives"),
        verbose_name=_("Validators"),
        blank=True,
        help_text=_("Student who validated the course_objective")
    )

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        return {"view_objective_activity"}

    @property
    def object_validator(self) -> 'ObjectiveValidatorMixin':
        return self.activity_objective_validator

    @property
    def related_entity(self) -> BasicModelMixin:
        return self.activity


class ResourceObjective(EntityObjective):
    """
    This object links an course_objective with a resource
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name=_("resource_objectives"),
        verbose_name=_("Objective")
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name=_("resource_objectives"),
        verbose_name=_("Resource")
    )
    validators = models.ManyToManyField(
        get_user_model(),
        through="ResourceObjectiveValidator",
        related_name=_("resource_objectives"),
        verbose_name=_("Validators"),
        blank=True,
        help_text=_("Student who validated the course_objective")
    )

    def _get_user_perms(self, user: get_user_model()) -> Set[str]:
        return {"view_objective_resource"}

    @property
    def object_validator(self) -> 'ObjectiveValidatorMixin':
        return self.resource_objective_validator

    @property
    def related_entity(self) -> BasicModelMixin:
        return self.resource


class ObjectiveValidatorMixin(models.Model):
    slug = models.SlugField(unique=True)
    validated = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Validated the…"))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """
        save() method is overridden to generate the slug field.
        :return:
        """
        self.slug = generate_slug_for_model(self.__class__, self)
        super().save(force_insert, force_update, using, update_fields)


class CourseObjectiveValidator(ObjectiveValidatorMixin):
    course_objective = models.ForeignKey(
        CourseObjective,
        on_delete=models.CASCADE,
        related_name="course_objective_validator",
        verbose_name=_("Course objective")
    )
    student = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="course_objective_validator",
        verbose_name=_("Student"),
    )

    def slug_generator(self):
        return f"{self.course_objective.objective.ability}-{str(self.student)}-" \
               f"{self.course_objective.related_entity.name}"


class ActivityObjectiveValidator(ObjectiveValidatorMixin):
    """
    An activity resource_objective validator.
    """
    activity_objective = models.ForeignKey(
        ActivityObjective,
        on_delete=models.CASCADE,
        related_name="activity_objective_validator",
        verbose_name=_("Activity objective"),
    )
    student = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="activity_objective_validator",
        verbose_name=_("Student"),
    )

    def slug_generator(self):
        return f"{self.activity_objective.objective.ability}-{str(self.student)}-" \
               f"{self.activity_objective.related_entity.name}"


class ResourceObjectiveValidator(ObjectiveValidatorMixin):
    """
    A resource resource_objective validator.
    """
    resource_objective = models.ForeignKey(
        ResourceObjective,
        on_delete=models.CASCADE,
        related_name="resource_objective_validator",
        verbose_name=_("Resource objective"),
    )
    student = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="resource_objective_validator",
        verbose_name=_("Student"),
    )

    def slug_generator(self):
        return f"{self.resource_objective.objective.ability}-{str(self.student)}-" \
               f"{self.resource_objective.related_entity.name}"


class ObjectCollaboratorMixin(models.Model):
    """
    This model is used as base for any entity-collaborator model. A collaborator always has a specific role.
    """
    role = models.CharField(
        max_length=20,
        choices=[(role.name, role.value) for role in CollaboratorRole],
        default=CollaboratorRole.NON_EDITOR_TEACHER.name,
        verbose_name=_("Role")
    )

    @property
    @abc.abstractmethod
    def collaborator(self) -> get_user_model():
        """
        Get the entity collaborator. It is often defined explicitly in subclasses using a foreign key. This property,
         here, ensures that calling it from this class with not raise any syntax error.

        :return: the entity collaborator
        :rtype: get_user_model()
        """

    @property
    @abc.abstractmethod
    def related_object(self) -> BasicModelMixin:
        """
        The corresponding related object: Course, Activity or Resource for instance. This is used to access the related
        object without knowing it explicitly (as this function is defined and used in parent class)

        :return: the related object instance
        :rtype: BasicModelMixin
        """
        raise NotImplementedError

    # noinspection PyArgumentEqualDefault
    created = models.DateTimeField(auto_now_add=True, auto_now=False, verbose_name=_("Since the"))
    # noinspection PyArgumentEqualDefault
    updated = models.DateTimeField(auto_now_add=False, auto_now=True, verbose_name=_("Last updated the"))

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        if self.collaborator == self.related_object.author:
            raise ValidationError(
                _("%(user)s is already author of the course. It cannot be added as a collaborator.")
                % {"user": self.collaborator}
            )

    def __str__(self):
        return _("%(user)s is ”%(role)s” in the %(object_name)s “%(object)s”") % {
            "user": self.collaborator,
            "role": CollaboratorRole[self.role].value,
            "object_name": _(self.related_object.__class__.__name__.lower()),
            "object": self.related_object
        }

    class Meta:
        abstract = True


class CourseCollaborator(ObjectCollaboratorMixin):
    """
    The concrete class to express the collaboration link for a user on a course.
    """
    collaborator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="course_collaborators",
        verbose_name=_("Collaborator")
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_collaborators",
        verbose_name=_("Course")
    )

    # noinspection PyMissingOrEmptyDocstring
    @property
    def related_object(self) -> BasicModelMixin:
        return self.course

    # noinspection PyMissingOrEmptyDocstring
    def clean(self):
        super().clean()
        if self.collaborator in self.course.students.all():
            raise ValidationError(
                _("%(user)s cannot be added as a collaborator on this course. %(user)s is already "
                  "a student, a user cannot be both.") % {"user": self.collaborator}
            )

    class Meta:
        ordering = ["course__updated", "role"]
        unique_together = ("collaborator", "course")
        verbose_name = pgettext_lazy("Course collaborators verbose name (singular form)", "course collaborator")
        verbose_name_plural = pgettext_lazy("Course collaborators verbose name (plural form)", "course collaborators")


class ActivityCollaborator(ObjectCollaboratorMixin):
    """
    The concrete class to express the collaboration link for a user on an activity.
    """
    collaborator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="activity_collaborators",
        verbose_name=_("Collaborator")
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name="activity_collaborators",
        verbose_name=_("Activity")
    )

    # noinspection PyMissingOrEmptyDocstring
    @property
    def related_object(self) -> BasicModelMixin:
        return self.activity

    class Meta:
        ordering = ["activity__updated", "role"]
        unique_together = ("collaborator", "activity")
        verbose_name = pgettext_lazy("Activity collaborators verbose name (singular form)", "activity collaborator")
        verbose_name_plural = pgettext_lazy("Activity collaborators verbose name (plural form)",
                                            "activity collaborators")


class ResourceCollaborator(ObjectCollaboratorMixin):
    """
    The concrete class to express the collaboration link for a user on a resource.
    """
    collaborator = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="resource_collaborators",
        verbose_name=_("Collaborator")
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="resource_collaborators",
        verbose_name=_("Resource")
    )

    # noinspection PyMissingOrEmptyDocstring
    @property
    def related_object(self) -> BasicModelMixin:
        return self.resource

    class Meta:
        ordering = ["resource__updated", "role"]
        unique_together = ("collaborator", "resource")
        verbose_name = pgettext_lazy("Resource collaborators verbose name (singular form)", "resource collaborator")
        verbose_name_plural = pgettext_lazy("Resource collaborators verbose name (plural form)",
                                            "resource collaborators")


def get_progression_on_course_for_user(course: Course, student: get_user_model()) -> dict:
    """
    This method return a dict which contains progression information for a student given.
    This could be exported as json or used in rest-API
    todo: Order the course_objective in the Bloom taxonomy order. Maybe use the Enum indexes
    :param course: Course
    :param student: get_user_model()
    :return: dict()
    """

    # Number of course_objective in the course
    objective_taxonomy_total = 0
    # Number of course_objective not validated
    objective_taxonomy_total_validated = 0
    # List of dict where will will find the objectives and associate information
    objectives_in_course_information = []
    # Information for an course_objective
    objective_taxonomy_information = dict()

    # Iterating on objectives in course. get_all_objectives() gives all objectives on course (activities and
    # resources included)
    for objective in course.get_all_objectives():
        # Information on an course_objective
        objective_basic_information = dict()

        # 'objective_ability' is simply the course_objective ability, independently of course,activity,resource
        objective_basic_information["objective_ability"] = objective.ability

        # Validated is a boolean which will say if course_objective is validated
        # on almost one Course/Activity/Resource
        objective_basic_information["validated"] = False

        # Query to get CourseObjective using this course_objective
        objective_on_course = CourseObjective.objects.filter(
            objective=objective,
            course=course
        )

        # Query to get CourseObjective using this course_objective
        objective_on_activity = ActivityObjective.objects.filter(
            objective=objective,
            activity__course_activities__course=course
        )

        # Query to get ResourceObjective using this course_objective
        objective_on_resource = ResourceObjective.objects.filter(
            objective=objective,
            resource__activities__course_activities__course=course
        )

        # The 3 following block get the ObjectObjective and put it in the dict
        if objective_on_course.exists():
            objective_basic_information["on_course"] = objective_on_course.all()

        if objective_on_activity.exists():
            objective_basic_information["on_activity"] = objective_on_activity.all()

        if objective_on_resource.exists():
            objective_basic_information["on_resource"] = objective_on_resource.all()

        # An course_objective is validated if he is validated in on of the course/activity/resource
        objective_basic_information["validated"] = \
            any(
                student in objective_on_resource_object.validators.all()
                for objective_on_resource_object in objective_on_resource) or \
            any(
                student in objective_on_activity_object.validators.all()
                for objective_on_activity_object in objective_on_activity) or \
            any(
                student in objective_on_course_object.validators.all()
                for objective_on_course_object in objective_on_course)

        objectives_in_course_information.append(objective_basic_information)

        # here we updated all the needed statistics
        for all_objectives in [objective_on_course, objective_on_activity, objective_on_resource]:
            for obj in all_objectives:
                if obj.taxonomy_level not in objective_taxonomy_information:
                    objective_taxonomy_information[obj.taxonomy_level] = dict()
                    objective_taxonomy_information[obj.taxonomy_level]["number_validation"] = 0
                    objective_taxonomy_information[obj.taxonomy_level]["total"] = 0

                if student in obj.validators.all():
                    objective_taxonomy_information[obj.taxonomy_level]["number_validation"] += 1
                    objective_taxonomy_total_validated += 1
                objective_taxonomy_information[obj.taxonomy_level]["total"] += 1

        objective_taxonomy_total += len(objective_on_course) + len(objective_on_activity) + len(
            objective_on_resource)

    # Update the size of progress for each TaxonomyLevel
    for level in objective_taxonomy_information:
        objective_taxonomy_information[level]["progress_dimension"] = \
            int(objective_taxonomy_information[level][
                    'total'] / objective_taxonomy_total * 100 * objective_taxonomy_information[level][
                    "number_validation"]
                / objective_taxonomy_information[level]["total"])

        objective_taxonomy_information[level]["progress_total"] = \
            int(100 * objective_taxonomy_information[level]["number_validation"]
                / objective_taxonomy_information[level]["total"])

    final_student_progression = dict()
    final_student_progression["objective_taxonomy_total"] = objective_taxonomy_total
    final_student_progression["objectives_in_course_information"] = objectives_in_course_information
    final_student_progression["objective_taxonomy_information"] = objective_taxonomy_information

    return final_student_progression
