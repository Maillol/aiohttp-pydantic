"""
Utility to write Async Api Specifications using the Python language.
"""


class AsyncAPISpec:
    def __init__(self):
        self._spec = {
            "asyncapi": "2.0.0",
            "info": {"version": "1.0.0", "title": "AsyncAPI Application"},
            "servers": {},
            "channels": {},
        }

    @property
    def info(self):
        return Info(self._spec)

    @property
    def servers(self):
        return Servers(self._spec)

    @property
    def channels(self):
        return Channels(self._spec)

    @property
    def spec(self):
        return self._spec


class Info:
    def __init__(self, spec: dict):
        self._spec = spec.setdefault("info", {})

    @property
    def title(self):
        return self._spec.get("title")

    @title.setter
    def title(self, title):
        self._spec["title"] = title

    @property
    def version(self):
        return self._spec.get("version")

    @version.setter
    def version(self, version):
        self._spec["version"] = version

    @property
    def description(self):
        return self._spec.get("description")

    @description.setter
    def description(self, description):
        self._spec["description"] = description


class Servers:
    def __init__(self, spec: dict):
        self._spec = spec.setdefault("servers", {})

    def add_server(self, name, url, protocol, description=""):
        self._spec[name] = {
            "url": url,
            "protocol": protocol,
            "description": description,
        }


class Channels:
    def __init__(self, spec: dict):
        self._spec = spec.setdefault("channels", {})

    def add_channel(self, name, description, subscribe_message=None, publish_message=None):
        channel = {"description": description}
        if subscribe_message:
            channel["subscribe"] = {"message": subscribe_message}
        if publish_message:
            channel["publish"] = {"message": publish_message}
        self._spec[name] = channel


class Message:
    def __init__(self, content_type, summary, payload):
        self.message = {
            "contentType": content_type,
            "summary": summary,
            "payload": payload,
        }

    def to_dict(self):
        return self.message
