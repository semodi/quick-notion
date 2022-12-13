import socket
from pathlib import Path

import dropbox
from pydantic import root_validator, validator
from pytion.api import PropertyValue

from .connection import Connection
from .dbox import upload
from .models import NotionField, PageHook, PageModel, PagePropertyModel

page_registry = {}


def page(name):
    def register_wrapper(cls):
        page_registry[name] = cls
        return cls

    return register_wrapper


class TaskProperties(PagePropertyModel):
    Priority: PropertyValue = NotionField(
        "Medium", notion_type="select", cli_flag="--priority"
    )
    Tags: PropertyValue = NotionField(
        ["From CLI"], notion_type="multi_select", cli_flag="--tags"
    )
    Projects: PropertyValue = NotionField(
        [], notion_type="relation", cli_flag="--projects", related_db="project"
    )


class LogProperties(PagePropertyModel):
    Tags: PropertyValue = NotionField(
        ["From CLI"], notion_type="multi_select", cli_flag="--tags"
    )
    Projects: PropertyValue = NotionField(
        [], notion_type="relation", cli_flag="--projects", related_db="project"
    )


class MediaProperties(PagePropertyModel):
    Files: PropertyValue = NotionField(
        [], notion_type="relation", cli_flag=None, related_db="file"
    )
    Tags: PropertyValue = NotionField(
        ["From CLI"], notion_type="multi_select", cli_flag=None
    )
    Type: PropertyValue = NotionField(
        "Academic Journal", notion_type="select", cli_flag=None
    )


class FileProperties(PagePropertyModel):
    Path: PropertyValue = NotionField(..., notion_type="rich_text", cli_flag="path")
    Device: PropertyValue = NotionField(
        [socket.gethostname()], notion_type="multi_select", cli_flag="--device"
    )
    Tags: PropertyValue = NotionField(
        ["From CLI"], notion_type="multi_select", cli_flag="--tags"
    )
    Description: PropertyValue = NotionField(
        "", notion_type="rich_text", cli_flag="--description"
    )
    Projects: PropertyValue = NotionField(
        [], notion_type="relation", cli_flag="--projects", related_db="project"
    )
    Tasks: PropertyValue = NotionField(
        [], notion_type="relation", cli_flag="--tasks", related_db="task"
    )
    Staging: PropertyValue = NotionField(True, notion_type="checkbox", cli_flag=None)
    Link: PropertyValue = NotionField("", notion_type="url", cli_flag="--upload")
    is_paper: PropertyValue = NotionField(
        False, notion_type="checkbox", cli_flag="--paper"
    )
    dropbox_path: PropertyValue = NotionField(
        "", notion_type="rich_text", cli_flag=None
    )

    @validator("Path", pre=True)
    def make_path_absolute(v):
        return str(Path(v).expanduser().absolute())

    @root_validator
    def upload_file(cls, values):
        if "Link" in values and values["Link"].value:
            dbx = dropbox.Dropbox(Connection.config["dropbox-token"])
            res = upload(
                dbx,
                str(values["Path"].value),
                "Apps",
                "quick-notion",
                values["Link"],
                overwrite=True,
            )
            link = dbx.sharing_create_shared_link(res.path_lower).url
            values["Link"] = PropertyValue.create("url", link)
            values["dropbox_path"] = PropertyValue.create("rich_text", res.path_lower)
        return values


@page("task")
class Task(PageModel):
    properties: TaskProperties


@page("log")
class Log(PageModel):
    properties: LogProperties


@page("paper")
class Paper(PageModel):
    properties: MediaProperties


@page("file")
class File(PageModel):
    properties: FileProperties
    _hooks: list[PageHook] = [
        PageHook(
            page_model=Paper,
            parent=Connection.get_db("media").obj,
            property_map={},
            foreign_relation="Files",
        )
    ]
