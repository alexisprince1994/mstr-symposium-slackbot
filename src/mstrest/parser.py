import json
from itertools import chain
from types import GeneratorType


class Attribute(object):
    def __init__(self, name, id, forms):
        self.name = name
        self.id = id
        self.forms = forms
        self.mstr_type = "Attribute"

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["id"], d["forms"])

    def __str__(self):
        return self.name

    def __repr__(self):
        return (
            f"Attribute({self.name}, {self.id}, {self.forms}, {self.attribute_index})"
        )

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        # Not actually necessary, but is more clear.
        return not (self == other)


class Metric(object):
    def __init__(self, name, id, thresholds, min_val, max_val, number_formatting):
        self.name = name
        self.id = id
        self.thresholds = thresholds
        self.min_val = min_val
        self.max_val = max_val
        self.number_formatting = number_formatting
        self.mstr_type = "Metric"

    @classmethod
    def from_dict(cls, d):

        return cls(
            d["name"],
            d["id"],
            d.get("thresholds", None),
            d.get("min", None),
            d.get("max", None),
            d.get("numberFormatting", None),
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Metric({self.name}, {self.id}, {self.min_val}, \
      {self.max_val}, {self.number_formatting}"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not (self == other)


class Threshold(object):
    def __init__(self, name, qualification_type, format, condition):
        self.name = name
        self.qualification_type
        self.format = format
        self.condition = condition

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["type"], d["format"], d["condition"])


class MstrParser(object):
    def __init__(self, response):
        self.response = response
        self.attributes = []
        self.metrics = []
        self._get_response_definitions()

    def _get_response_definitions(self):

        """
    Populates the attributes and metrics attributes of the instance.
    These provide metadata information about which attributes and 
    metrics are in the JSON response.
    
    :return: None
    """

        definitions = self.response["result"]["definition"]

        for attribute in definitions["attributes"]:
            self.attributes.append(Attribute.from_dict(attribute))

        for metric in definitions.get("metrics", []):
            self.metrics.append(Metric.from_dict(metric))

    def parse_rows(self):

        """
    Top level function that returns a generator of records from the 
    Microstrategy data. 

    :return: generator of dictionaries
    """

        data_payload = self.response["result"]["data"]["root"]["children"]
        # Returning a list of maybe generators (of varying length), then combining
        # them using chain from itertools for faster iteration.
        data_generators = [self._parse_level(mstr_data) for mstr_data in data_payload]
        for data_generator in chain(*data_generators):
            reduced_generator = self._exhaust_generators(data_generator)
            yield reduced_generator

    def _exhaust_generators(self, gen):

        """
    For each attribute in the response, the generator gets another level
    deeper. So, if there is 1 attribute, its a generator of values
    If there are 2 attributes, its a generator of generators of values
    and so on. This function eliminates that by exhausting all
    sub-generators allowing the top level function to return 
    one generator that has all of the data.
    :return: dictionaries
    """

        if isinstance(gen, GeneratorType):
            for generator in gen:
                return self._exhaust_generators(generator)
        else:
            return gen

    def _parse_level(self, d, parents=None):

        """
    Recursive function that parses each "level" of the response due to its
    nested nature. This flattens it out, meaning that each record that goes 
    out, will be in one semi-flat dictionary instead of the nested mess.

    :param d: dict
    :return: dict
    """

        d_out = {}
        # not doing if parents is not None because we need to check
        # for the empty dictionary as well.
        if parents:
            d_out.update(parents)

        attribute_name = self.attributes[d["element"]["attributeIndex"]].name
        d_out[attribute_name] = d["element"]["name"]

        # ORDER MATTERS FOR THESE CHECKS
        # AS THIS IS A RECURSIVE FUNCTION THAT YIELDS GENERATORS
        if "metrics" in d:
            d_out["metrics"] = d["metrics"]
            yield d_out

        if "children" in d:
            yield from [self._parse_level(child, d_out) for child in d["children"]]

        if "metrics" not in d and "children" not in d:
            yield d_out
