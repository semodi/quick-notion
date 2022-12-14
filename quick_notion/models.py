import argparse
from functools import wraps
from typing import Callable, Optional

from pick import pick
from pydantic import BaseModel, Field, validator
from pytion.api import LinkTo, PropertyValue

from .connection import Connection

notion_types = {
    "rich_text": "?",
    "url": "?",
    "select": "?",
    "multi_select": "+",
    "checkbox": "?",
    "relation": "?",
    None: "?",
}


@wraps(Field)
def NotionField(*args, **kwargs):
    if "notion_type" not in kwargs:
        raise ValueError("Must provide notion_type kwarg")
    notion_type = kwargs.pop("notion_type", None)
    if notion_type and notion_type not in notion_types:
        raise TypeError(f"notion_type {notion_type} not supported")
    cli_flag = kwargs.pop("cli_flag", None)
    return Field(*args, notion_type=notion_type, cli_flag=cli_flag, **kwargs)


class PagePropertyModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    @validator("*", pre=True)
    def validate_relations(cls, v, field):
        if not "notion_type" in field.field_info.extra:
            return v
        notion_type = field.field_info.extra["notion_type"]
        if notion_type is None:
            return v
        if notion_type != "relation":
            return v
        if v is not None:
            return v
        related_db = Connection.get_db(field.field_info.extra["related_db"])
        db_entries = related_db.db_query()
        entries = {str(entry): entry.id for entry in db_entries.obj}
        title = f"Please choose your {field.name}(s) (press SPACE to mark, ENTER to continue): "
        options = list(entries)
        selected = pick(options, title, multiselect=True, min_selection_count=1)
        prop = PropertyValue.create(
            notion_type, [{"id": entries[sel[0]]} for sel in selected]
        )
        return prop

    @validator("*", pre=True, always=True)
    def validate_notion_fields(cls, v, field):
        if not "notion_type" in field.field_info.extra:
            return v
        notion_type = field.field_info.extra["notion_type"]
        if notion_type is None:
            return v
        if notion_type == "relation":
            if not v:
                return PropertyValue.create("relation", [])
            else:
                return v
        return PropertyValue.create(notion_type, v)


class PageHook:
    def __init__(
        self,
        page_model,
        parent=None,
        property_map=None,
        condition: Callable = None,
        foreign_relation=None,
    ):
        self.page_model = page_model
        self.condition = condition
        self.parent = parent
        self.property_map = property_map or {}
        self.foreign_relation = foreign_relation

    def __call__(self, source_page, id=None):
        if self.condition is None or self.condition(source_page):
            source_properties = source_page.properties.dict()
            mapped_properties = {
                self.property_map[key]: val
                for key, val in source_properties.items()
                if key in self.property_map
            }
            if self.foreign_relation and id:
                mapped_properties[self.foreign_relation] = PropertyValue.create(
                    "relation", [{"id": id}]
                )
            mapped_properties = self.page_model.__fields__["properties"].type_(
                **mapped_properties
            )
            page = self.page_model(
                title=source_page.title,
                parent=self.parent,
                properties=mapped_properties,
            )
            return page


class PageModel(BaseModel):

    title: str
    parent: Optional[LinkTo] = None
    properties: Optional[PagePropertyModel] = None
    _hooks: list[PageHook] = []

    class Config:
        arbitrary_types_allowed = True

    @validator("parent", pre=True)
    def link_parent(cls, v):
        if not v:
            return
        if isinstance(v, LinkTo):
            return v
        return LinkTo(from_object=v)

    def create_page(self, client):
        pages = client.pages
        created = pages.page_create(
            parent=self.parent, properties=self.properties.dict(), title=self.title
        )
        for hook in self._hooks:
            hook_page = hook(self, created.obj.id)
            if hook_page:
                hook_page.create_page(client)

    @classmethod
    def from_cli(cls, parent=None):
        parser = argparse.ArgumentParser()
        parser.add_argument("mode")
        parser.add_argument("title")
        property_map = {}
        for prop_name, prop_field in cls.__fields__[
            "properties"
        ].type_.__fields__.items():
            cli_flag = prop_field.field_info.extra["cli_flag"]
            if not cli_flag:
                continue
            notion_type = prop_field.field_info.extra["notion_type"]
            property_map[prop_name] = cli_flag.replace("--", "")
            if not prop_field.default is None:
                if notion_type == "checkbox":
                    parser.add_argument(
                        cli_flag,
                        action="store_true",
                        default=prop_field.default,
                    )
                else:
                    parser.add_argument(
                        cli_flag,
                        nargs=notion_types[notion_type],
                        default=prop_field.default,
                    )
            else:
                cli_flag = cli_flag.replace("--", "")
                parser.add_argument(cli_flag)
        args = parser.parse_args()
        return cls(
            title=args.title,
            parent=parent,
            properties={key: getattr(args, val) for key, val in property_map.items()},
        )
