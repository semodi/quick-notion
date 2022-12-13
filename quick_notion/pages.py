import socket
from pathlib import Path

import dropbox
from pydantic import root_validator, validator
from pytion.api import PropertyValue

from .connection import Connection
from .dbox import upload
from .models import NotionField, PageModel, PagePropertyModel

page_registry = {}


def page(name):
    def register_wrapper(cls):
        page_registry[name] = cls

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
    Link: PropertyValue = NotionField("", notion_type="rich_text", cli_flag="--upload")
    dropbox_path: PropertyValue = NotionField(
        "", notion_type="rich_text", cli_flag=None
    )

    @validator("Path", pre=True)
    def make_path_absolute(v):
        return str(Path(v).expanduser().absolute())

    @root_validator
    def upload_file(cls, values):
        if "Link" in values and values["Link"]:
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
            values["Link"] = PropertyValue.create("rich_text", link)
            values["dropbox_path"] = PropertyValue.create("rich_text", res.path_lower)
        return values


@page("task")
class Task(PageModel):
    properties: TaskProperties


@page("file")
class File(PageModel):
    properties: FileProperties


@page("log")
class Log(PageModel):
    properties: LogProperties
