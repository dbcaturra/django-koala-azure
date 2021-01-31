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
from typing import Type, Union, SupportsInt, Callable

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.views.generic.edit import FormMixin

from learning.forms import BasicSearchForm
from learning.models import BasicModelMixin


# noinspection PyMissingOrEmptyDocstring
class InvalidFormHandlerMixin(FormMixin):

    def __show_messages(self, form):
        for field_errors in form.errors.as_data().values():
            for validation_error in field_errors:
                for message in validation_error.messages:
                    # noinspection PyUnresolvedReferences
                    messages.error(self.request, message)
        return super().form_invalid(form)

    def form_invalid(self, form):  # pragma: no cover
        self.__show_messages(form)
        return super().form_invalid(form)


def int_or_default(value: Union[str, bytes, SupportsInt], default: int) -> int:
    """
    Transforms the value given in parameter into a int, is possible. Otherwise, use the default value.

    :param value: the value to transform into an int
    :type value: object
    :param default: the default value to use, if the conversion fails.
    :type default: int
    :return: the converted value, or the default one.
    :rtype: int
    """
    try:
        value = int(value)
    except ValueError:
        value = default
    return value


def get_attr_form_query_dict_or_kwargs(attr_name: str, query_dict: dict, callback: Callable, default: int, **kwargs):
    """
    Get a value from the given query_dict or from kwargs if absent from the first one. The callback function is used
    to convert the value and if this fails, to fallback to the given default value.

    :param attr_name: the attribute name to look for.
    :type attr_name: str
    :param query_dict: the query dict in which to look for the attribute
    :type query_dict: dict
    :param callback: the function to use in order to convert the attribute
    :type callback: Callable
    :param default: the default value for the attribute, if none is found
    :type default: int
    :param kwargs: the known args in which to look for the attribute first.
    :type kwargs: dict
    :return: the value extracted from query_dict or kwargs if present, default value instead.
    """
    if attr_name in kwargs.keys():
        value = callback(kwargs.get(attr_name, default), default)
    else:
        try:
            value = callback(query_dict.get(attr_name, default), default)
        except KeyError:
            value = default
    return value


# noinspection PyMissingOrEmptyDocstring
class PaginatorFactory:

    @classmethod
    def get_paginator_as_context(cls, objects: QuerySet, query_dict: dict, prefix: str = None,
                                 nb_per_page: int = 3, **kwargs) -> dict:
        """
        This transforms the given objects into a dictionary, suitable to be used in view context. The dictionary is
        build with a few properties:
        * paginator: the paginator object
        * page_obj: the paginator page
        * has_obj: if the object_list is not empty. Here, None is not equal to False in templates
          (you should use `== False` in templates) to determine whether there are no objects in the list.
        * nb_per_page: the number of elements per page
        * current_page: the current page number

        :param objects: the objects to paginate
        :type: objects: QuerySet
        :param query_dict: a dictionary containing a “query” key, with the filtering terms.
        :type query_dict: dict
        :param prefix: the prefix to set for context attributes.
        :type prefix: str
        :param nb_per_page: the number of elements to display on each paginator page.
        :type nb_per_page: int
        :param kwargs: other known arguments
        :type kwargs: dict
        :return: a dictionary, enriched with objects, paginated using the Paginator class.
        :rtype: dict
        """
        # Make attribute names
        paginator_str = "{}_paginator".format(prefix) if prefix else "paginator"
        page_obj_str = "{}_page_obj".format(prefix) if prefix else "page_obj"
        has_obj_str = "{}_has_obj".format(prefix) if prefix else "has_obj"
        nb_per_page_str = "{}_nb_per_page".format(prefix) if prefix else "nb_per_page"
        current_page_str = "{}_page".format(prefix) if prefix else "page"

        # Extract values: if value is defined in **kwargs, it has priority over the query dict
        nb_per_page = get_attr_form_query_dict_or_kwargs(
            nb_per_page_str, query_dict, int_or_default, nb_per_page, **kwargs
        )
        current_page = get_attr_form_query_dict_or_kwargs(current_page_str, query_dict, int_or_default, 1, **kwargs)

        paginator = Paginator(objects, nb_per_page)
        return {
            paginator_str: paginator,
            page_obj_str: paginator.get_page(current_page),
            nb_per_page_str: nb_per_page,
            has_obj_str: bool(paginator.object_list)
        }


# noinspection PyMissingOrEmptyDocstring
class SearchQuery:

    @classmethod
    def search_query_as_context(cls, obj_class: Type[BasicModelMixin], query_dict: dict) -> dict:
        """
        Get all the objects of a specific object type given the query

        :param obj_class: the object class type for which to query objects
        :type obj_class: Type[BasicModelMixin]
        :param query_dict: the query dict that contains a “query” key. This can be POST or GET for instance.
        :type query_dict: dict
        :return: a dictionary containing the results of this search after a call to PaginatorFactor with the search
            prefix.
        :rtype: dict
        """
        context = dict()
        form = BasicSearchForm(data=query_dict)
        if form.is_valid() and form.cleaned_data.get("query", str()):
            query = form.cleaned_data.get("query", str())
            queryset = obj_class.objects.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            ).all()
            context.update(PaginatorFactory.get_paginator_as_context(queryset, query_dict, prefix="search"))
        context["form"] = form
        return context
