"""
API that authorizes access to objects in object storage
"""
from dataclasses import dataclass
import json
from typing import Any
from ixoncdkingress.function.context import FunctionContext, FunctionResource
from ixoncdkingress.function.objectstorage.types import ResourceType, PathMapping, PathResponse, \
    ListPathResponse, PathData

@dataclass
class AssetAppResult:
    """
    The result of a request for asset app config objects
    """

    values: str
    stateValues: str # pylint: disable=C0103

@dataclass
class ObjectMeta:
    """
    The metadata of an object in the object storage
    """

    id: str
    name: str | None = None
    order: int | None = None
    size: int | None = None
    type: str | None = None
    category: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ObjectMeta | None":
        """
        Creates an ObjectMeta instance from a dictionary

        Returns None if it cannot be parsed
        """
        try:
            return cls(
                id=data["id"],
                name=data.get("name"),
                order=data.get("order"),
                size=data.get("size"),
                type=data.get("type"),
                category=data.get("category"),
            )
        except (KeyError, ValueError):
            return None


def _has_access_to_files_of_resource(
        company: FunctionResource,
        resource: FunctionResource,
    ) -> bool:
    """
    Validates if the caller is authorized to access files for the given
    resource.
    """
    assert resource.permissions is not None  # type hint
    assert company.permissions is not None  # type hint
    if (
            'MANAGE_AGENT' not in resource.permissions and
            'COMPANY_ADMIN' not in company.permissions
        ):
        return False

    return True

def _format_path_for_resource(resource: FunctionResource, typ: ResourceType) -> str:
    """
    Formats the path at which files for the given resource are stored
    """
    root = 'assets'

    if typ != ResourceType.ASSET:
        root = 'agents'

    return f'{root}/{resource.public_id}/'

def _create_single_response(
        resource: FunctionResource, typ: ResourceType,
    ) -> PathResponse:
    """
    Creates a single-path response, as is
    used by authorize_upload, authorize_download & authorize_delete
    """
    return PathResponse(
        result='success',
        data=PathData(
            path=_format_path_for_resource(resource, typ),
        ),
    )

def _create_mapping_for_resource(res: tuple[FunctionResource, ResourceType]):
    resource, typ = res
    return PathMapping(
        publicId=resource.public_id,
        type=typ,
        path=_format_path_for_resource(resource, typ)
    )

def _create_multi_response(
    context: FunctionContext, resources: list[tuple[FunctionResource, ResourceType]]
) -> ListPathResponse:
    """
    Creates a multi-path response, as is used by authorize_list
    """
    mappings = list(map(_create_mapping_for_resource, resources))
    mappings.extend(
        _get_asset_app_config_object_mappings(
            context,
            [resource for resource, typ in resources if typ == ResourceType.ASSET],
        )
    )

    return ListPathResponse(
        result="success",
        data=mappings,
    )


def _add_asset_descendant_resources(
    context: FunctionContext,
    resources: list[tuple[FunctionResource, ResourceType]],
) -> list[tuple[FunctionResource, ResourceType]]:
    """
    Adds all resources that are descendants of the given asset to the given resources list
    """
    children: list[tuple[FunctionResource, ResourceType]] = []
    for resource, r_type in resources:
        if r_type == ResourceType.ASSET:
            result: list[dict[str, str]] = context.api_client.get(
                "AssetDescendantList",
                {"publicId": resource.public_id, "fields": "publicId,name"},
            )["data"]
            children.extend(
                [
                    (
                        FunctionResource(
                            public_id=res["publicId"],
                            name=res["name"],
                            custom_properties={},
                            permissions=set(),
                        ),
                        ResourceType.ASSET,
                    )
                    for res in result
                ]
            )

    resources.extend(children)
    return resources

def _get_asset_app_config_object_mappings(
    context: FunctionContext,
    asset_resources: list[FunctionResource],
) -> list[PathMapping]:
    """
    Returns a list of all asset app config objects
    """
    if not context.template or not asset_resources:
        return []

    pub_ids = [f'"{res.public_id}"' for res in asset_resources]
    result: list[dict[str, Any]] = context.api_client.get(
        "AssetAppConfigList",
        query={
            "filters": [
                f'eq(app.publicId,"{context.template.public_id}")',
                f"in(asset.publicId,{','.join(pub_ids)})",
            ],
            "fields": "values,stateValues",
        },
    )["data"]

    return [
        PathMapping(
            publicId=None,
            type=ResourceType.ASSET,
            path=f"assets/{file}",
        )
        for app in result
        if (files := _parse_asset_meta(AssetAppResult(
            values=app["values"],
            stateValues=app["stateValues"],
        )))
        for file in files
    ]


def _parse_asset_meta(asset_app_config: AssetAppResult | None) -> list[str]:
    """
    Parses the metadata of an asset
    """
    if not asset_app_config:
        return []

    objects = [
        ObjectMeta.from_dict(item)
        for item in json.loads(asset_app_config.values or "[]")
    ] + [
        ObjectMeta.from_dict(item)
        for item in json.loads(asset_app_config.stateValues or "[]")
    ]

    return [object.id for object in objects if object]


def _request_for(context: FunctionContext) -> tuple[FunctionResource, ResourceType] | None:
    """
    Detects the target resource of the request, preferring assets to agents.
    Will also return the type of the resource.
    """
    # A company is required in all cases
    if not context.company:
        return None

    target = context.agent
    typ = ResourceType.AGENT

    if context.asset:
        target = context.asset
        typ = ResourceType.ASSET

    if not target:
        return None

    return target, typ

def _authorize_single(
    context: FunctionContext,
    uuid: str | None,
    check_has_manage: bool,
    upload: bool = False,
) -> PathResponse | None:
    if (target_typ := _request_for(context)) is None:
        return None

    target, typ = target_typ

    assert context.company  # type check

    if check_has_manage and not _has_access_to_files_of_resource(
            context.company,
            target,
        ):
        return None

    if typ == ResourceType.ASSET and uuid:
        path = f"assets/{uuid}/"

        if upload:
            return PathResponse(result="success", data=PathData(path=path))

        mappings = _get_asset_app_config_object_mappings(
            context,
            [
                target
                for target, _ in _add_asset_descendant_resources(
                    context, [(target, typ)]
                )
            ],
        )
        if f"assets/{uuid}" in [mapping["path"] for mapping in mappings]:
            return PathResponse(result="success", data=PathData(path=path))

    return _create_single_response(target, typ)

@FunctionContext.expose
def authorize_upload(context: FunctionContext, uuid: str | None = None) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to upload a blob to the object storage.
    """
    return _authorize_single(context, uuid, True, upload=True)

@FunctionContext.expose
def authorize_list(
        context: FunctionContext
    ) -> ListPathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to get the blob list from the object storage.
    """
    if (target_typ := _request_for(context)) is None:
        return None

    target, typ = target_typ
    resources = [(target, typ)]

    # If the target was an asset with a linked agent,
    # we should also return a path mapping for that agent
    if typ == ResourceType.ASSET and context.agent is not None:
        resources.append((context.agent, ResourceType.AGENT))

    _add_asset_descendant_resources(context, resources)

    return _create_multi_response(context, resources)

@FunctionContext.expose
def authorize_download(context: FunctionContext, uuid: str | None = None) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to download a blob from the object storage.
    """
    return _authorize_single(context, uuid, False)

@FunctionContext.expose
def authorize_update(context: FunctionContext, uuid: str | None = None) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to update a blob in the object storage.
    """
    return _authorize_single(context, uuid, True)

@FunctionContext.expose
def authorize_delete(context: FunctionContext, uuid: str | None = None) -> PathResponse | None:
    """
    Method to validate if and where the caller is allowed
    to delete a blob from the object storage.
    """
    return _authorize_single(context, uuid, True)
