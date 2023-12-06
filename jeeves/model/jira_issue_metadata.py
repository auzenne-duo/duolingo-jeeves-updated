from typing import List, Optional

import attr

from jeeves.model.custom_types import JSON


@attr.s(kw_only=True)
class JiraIssueFieldAllowedValue:
    id: str = attr.ib()
    name: str = attr.ib()  # e.g. Crowns, Leaderboards

    @classmethod
    def from_json(cls, value_json: JSON) -> "JiraIssueFieldAllowedValue":
        return cls(
            id=value_json["id"],
            # Some fields use value for the human-readable value, others use name.
            name=value_json["value"] if "value" in value_json else value_json["name"],
        )


@attr.s(kw_only=True)
class JiraIssueFieldMetaData:
    key: str = attr.ib()  # e.g. customfield_10908
    name: str = attr.ib()  # e.g. Feature
    allowed_values: List[JiraIssueFieldAllowedValue] = attr.ib()

    @classmethod
    def from_json(cls, field_json: JSON) -> "JiraIssueFieldMetaData":
        return cls(
            key=field_json["key"],
            name=field_json["name"],
            allowed_values=[
                JiraIssueFieldAllowedValue.from_json(allowed_value)
                for allowed_value in field_json["allowedValues"]
            ]
            if "allowedValues" in field_json
            else [],
        )


@attr.s(kw_only=True)
class JiraIssueTypeMetaData:
    """
    This information is used to create JIRA issue requests using the correct custom field keys,
    IDs for issue types, IDs for field vales, etc.
    """

    id: str = attr.ib()
    name: str = attr.ib()  # e.g: Story, Bug
    fields: List[JiraIssueFieldMetaData] = attr.ib()
    codebase_field: Optional[JiraIssueFieldMetaData] = attr.ib(init=False, default=None)
    feature_field: Optional[JiraIssueFieldMetaData] = attr.ib(init=False, default=None)
    team_field: Optional[JiraIssueFieldMetaData] = attr.ib(init=False, default=None)

    def __attrs_post_init__(self):
        for field in self.fields:
            if field.name == "Codebase":
                self.codebase_field = field
            if field.name == "Feature":
                self.feature_field = field
            if field.name == "Team":
                self.team_field = field

    def codebase_field_key(self) -> Optional[str]:
        """
        Returns the key of our custom 'Codebase' field.
        """
        if self.codebase_field:
            return self.codebase_field.key
        else:
            return None

    def feature_field_key(self) -> Optional[str]:
        """
        Returns the key of our custom 'Feature' field.
        """
        if self.feature_field:
            return self.feature_field.key
        else:
            return None

    def team_field_key(self) -> Optional[str]:
        """
        Returns the key of our custom 'Team' field.
        """
        if self.team_field:
            return self.team_field.key
        else:
            return None

    def _allowed_feature_value_objects(self) -> List[JiraIssueFieldAllowedValue]:
        if self.feature_field:
            return self.feature_field.allowed_values
        else:
            return []

    def allowed_feature_values(self) -> List[str]:
        """
        Allowed values of our custom 'Feature' field; e.g. [Achievements, Stories, Leaderboards, ...]
        """
        return [allowed_value.name for allowed_value in self._allowed_feature_value_objects()]

    def get_id_for_allowed_feature_value(self, name: str) -> Optional[str]:
        """
        Key for allowed value of cusom 'Feature' field.

        parameters:
            name: str The name of the allowed value; e.g. Achievements
        """
        for value in self._allowed_feature_value_objects():
            if value.name == name:
                return value.id
        return None

    @classmethod
    def from_json(cls, issue_type_json: JSON) -> "JiraIssueTypeMetaData":
        return cls(
            id=issue_type_json["id"],
            name=issue_type_json["name"],
            fields=[
                JiraIssueFieldMetaData.from_json(field)
                for field in issue_type_json[
                    "fields"
                ].values()  # The list of fields is sent as a dict from key to field object for some reason.
            ],
        )
