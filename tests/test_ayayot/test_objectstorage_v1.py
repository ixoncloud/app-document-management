from typing import Callable
from unittest import mock

import pytest

from ixoncdkingress.function.api_client import ApiClient
from ixoncdkingress.function.objectstorage.types import PathResponse
from ixoncdkingress.function.context import FunctionContext, FunctionResource

from functions.ayayot import objectstorage_v1 as sut

@pytest.mark.parametrize('company_perms,res_perms,expected', [
    (set(), set(), False),
    ({'COMPANY_ADMIN'}, {'COMPANY_ADMIN'}, True),
    (set(), {'MANAGE_AGENT'}, True),
])
def test__has_access_to_files_of_resource(company_perms, res_perms, expected):
    mut = sut._has_access_to_files_of_resource

    company = mock.create_autospec(FunctionResource, instance=True)
    resource = mock.create_autospec(FunctionResource, instance=True)

    company.permissions = company_perms
    resource.permissions = res_perms

    assert expected is mut(company, resource)

@pytest.mark.parametrize('pubid,typ,expected', [
    ('assetpubid01', sut.ResourceType.ASSET, 'assets/assetpubid01/'),
    ('agentpubid01', sut.ResourceType.AGENT, 'agents/agentpubid01/'),
])
def test__format_path_for_resource(pubid, typ, expected):
    mut = sut._format_path_for_resource

    resource = mock.create_autospec(FunctionResource, instance=True)
    resource.public_id = pubid

    output = mut(resource, typ)

    assert expected == output

@mock.patch('functions.ayayot.objectstorage_v1._format_path_for_resource', autospec=True)
def test__create_single_response(_format_path_for_resource: mock.Mock):
    mut = sut._create_single_response

    resource = mock.sentinel.resource
    typ = mock.sentinel.type

    output = mut(resource, typ)

    assert {
        'result': 'success',
        'data': {
            'path': _format_path_for_resource.return_value
        }
    } == output

    assert [
        mock.call(resource, typ)
    ] == _format_path_for_resource.call_args_list

@mock.patch('functions.ayayot.objectstorage_v1._format_path_for_resource', autospec=True)
def test__create_multi_response(_format_path_for_resource: mock.Mock):
    mut = sut._create_multi_response

    res1 = mock.create_autospec(spec=FunctionResource, instance=True)
    res1.public_id = mock.sentinel.pubid1
    type1 = mock.sentinel.type1

    res2 = mock.create_autospec(spec=FunctionResource, instance=True)
    res2.public_id = mock.sentinel.pubid2
    type2 = mock.sentinel.type2

    resources = [
        (res1, type1),
        (res2, type2),
    ]

    output = mut(resources)

    assert {
        'result': 'success',
        'data': [
            sut.PathMapping(
                publicId=mock.sentinel.pubid1,
                path=_format_path_for_resource.return_value,
                type=type1,
            ),
            sut.PathMapping(
                publicId=mock.sentinel.pubid2,
                path=_format_path_for_resource.return_value,
                type=type2,
            )
        ]
    } == output

    assert [
        mock.call(res1, type1),
        mock.call(res2, type2),
    ] == _format_path_for_resource.call_args_list

def test__request_for_agent():
    mut = sut._request_for

    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)
    context.asset = None

    output = mut(context)

    assert (context.agent, sut.ResourceType.AGENT) == output

def test__request_for_asset():
    mut = sut._request_for

    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)

    output = mut(context)

    assert (context.asset, sut.ResourceType.ASSET) == output

def test__request_for_no_company():
    mut = sut._request_for

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.company = None

    assert None is mut(context)

def test__request_for_no_target():
    mut = sut._request_for

    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)
    context.agent = None
    context.asset = None

    assert None is mut(context)

@pytest.mark.parametrize('check', [
    pytest.param(True, id='with-check'),
    pytest.param(False, id='without-check'),
])
@mock.patch('functions.ayayot.objectstorage_v1._create_single_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._has_access_to_files_of_resource', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test__authorize_single(
        _request_for: mock.Mock,
        _has_access_to_files_of_resource: mock.Mock,
        _create_single_response: mock.Mock,
        check: bool,
    ):
    mut = sut._authorize_single

    _request_for.return_value = (mock.sentinel.target, mock.sentinel.type)

    context = mock.create_autospec(spec=FunctionContext, instance=True)

    output = mut(context, check_has_manage=check)

    assert _create_single_response.return_value is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    if check:
        assert [
            mock.call(context.company, mock.sentinel.target)
        ] == _has_access_to_files_of_resource.call_args_list
    else:
        assert [] == _has_access_to_files_of_resource.call_args_list

    assert [
        mock.call(mock.sentinel.target, mock.sentinel.type)
    ] == _create_single_response.call_args_list

@mock.patch('functions.ayayot.objectstorage_v1._has_access_to_files_of_resource', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test__authorize_single_no_target(
        _request_for: mock.Mock,
        _has_access_to_files_of_resource: mock.Mock,
    ):
    mut = sut._authorize_single

    _request_for.return_value = None

    context = mock.create_autospec(spec=FunctionContext, instance=True)

    assert None is mut(context, check_has_manage=mock.sentinel.check_has_manage)

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [] == _has_access_to_files_of_resource.call_args_list

@mock.patch('functions.ayayot.objectstorage_v1._create_single_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._has_access_to_files_of_resource', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test__authorize_single_no_access(
        _request_for: mock.Mock,
        _has_access_to_files_of_resource: mock.Mock,
        _create_single_response: mock.Mock,
    ):
    mut = sut._authorize_single

    _request_for.return_value = (mock.sentinel.target, mock.sentinel.type)
    _has_access_to_files_of_resource.return_value = False

    context = mock.create_autospec(spec=FunctionContext, instance=True)

    output = mut(context, check_has_manage=True)

    assert None is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [
        mock.call(
            context.company,
            mock.sentinel.target
        )
    ] == _has_access_to_files_of_resource.call_args_list

    assert [] == _create_single_response.call_args_list

@pytest.mark.parametrize('mut,check_has_manage', [
    (sut.authorize_upload, True),
    (sut.authorize_download, False),
    (sut.authorize_update, True),
    (sut.authorize_delete, True),
])
@mock.patch('functions.ayayot.objectstorage_v1._authorize_single', autospec=True)
def test_authorize(
        _authorize_single: mock.Mock,
        mut: Callable[[FunctionContext], PathResponse],
        check_has_manage: bool,
    ):
    context = mock.create_autospec(spec=FunctionContext, instance=True)

    output = mut(context)

    assert _authorize_single.return_value is output

    assert [
        mock.call(context, check_has_manage)
    ] == _authorize_single.call_args_list

@mock.patch('functions.ayayot.objectstorage_v1._create_multi_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test_authorize_list_agent(
        _request_for: mock.Mock,
        _create_multi_response: mock.Mock,
    ):
    mut = sut.authorize_list

    _request_for.return_value = (mock.sentinel.target, sut.ResourceType.AGENT)

    context = mock.create_autospec(spec=FunctionContext, instance=True)

    output = mut(context)

    assert _create_multi_response.return_value is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [
        mock.call([(mock.sentinel.target, sut.ResourceType.AGENT)])
    ] == _create_multi_response.call_args_list

@mock.patch(
    "functions.ayayot.objectstorage_v1._add_asset_descendant_resources", autospec=True
)
@mock.patch('functions.ayayot.objectstorage_v1._create_multi_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test_authorize_list_asset_with_linked_agent(
    _request_for: mock.Mock,
    _create_multi_response: mock.Mock,
    _add_asset_descendant_resources: mock.Mock,
):
    mut = sut.authorize_list

    _request_for.return_value = (mock.sentinel.target, sut.ResourceType.ASSET)

    context = mock.create_autospec(spec=FunctionContext, instance=True)

    output = mut(context)

    assert _create_multi_response.return_value is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [
        mock.call(
            context,
            [
                (mock.sentinel.target, sut.ResourceType.ASSET),
                (context.agent, sut.ResourceType.AGENT),
            ],
        ),
    ] == _add_asset_descendant_resources.call_args_list

    assert [
        mock.call([
            (mock.sentinel.target, sut.ResourceType.ASSET),
            (context.agent, sut.ResourceType.AGENT),
        ])
    ] == _create_multi_response.call_args_list

@mock.patch(
    "functions.ayayot.objectstorage_v1._add_asset_descendant_resources", autospec=True
)
@mock.patch('functions.ayayot.objectstorage_v1._create_multi_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test_authorize_list_asset_without_linked_agent(
    _request_for: mock.Mock,
    _create_multi_response: mock.Mock,
    _add_asset_descendant_resources: mock.Mock,
):
    mut = sut.authorize_list

    _request_for.return_value = (mock.sentinel.target, sut.ResourceType.ASSET)

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.agent = None

    output = mut(context)

    assert _create_multi_response.return_value is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [
        mock.call(context, [(mock.sentinel.target, sut.ResourceType.ASSET)]),
    ] == _add_asset_descendant_resources.call_args_list

    assert [
        mock.call([
            (mock.sentinel.target, sut.ResourceType.ASSET),
        ])
    ] == _create_multi_response.call_args_list

@mock.patch('functions.ayayot.objectstorage_v1._create_multi_response', autospec=True)
@mock.patch('functions.ayayot.objectstorage_v1._request_for', autospec=True)
def test_authorize_list_no_target(
        _request_for: mock.Mock,
        _create_multi_response: mock.Mock,
    ):
    mut = sut.authorize_list

    _request_for.return_value = None

    context = mock.create_autospec(spec=FunctionContext)

    output = mut(context)

    assert None is output

    assert [
        mock.call(context)
    ] == _request_for.call_args_list

    assert [] == _create_multi_response.call_args_list

def test__add_asset_descendant_resources():
    mut = sut._add_asset_descendant_resources

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.api_client = mock.create_autospec(spec=ApiClient, instance=True)

    context.api_client.get.return_value = {
        "data": [
            {"publicId": "assetpubid02", "name": "Asset"},
        ]
    }

    asset0 = (
        FunctionResource(
            public_id="assetpubid01",
            name="Asset",
            custom_properties={},
            permissions=set(),
        ),
        sut.ResourceType.ASSET,
    )
    agent0 = (
        FunctionResource(
            public_id="agentpubid01",
            name="Agent",
            custom_properties={},
            permissions=set(),
        ),
        sut.ResourceType.AGENT,
    )

    resources = [asset0, agent0]

    mut(context, resources)

    assert repr(
        [
            asset0,
            agent0,
            (
                FunctionResource(
                    public_id="assetpubid02",
                    name="Asset",
                    custom_properties={},
                    permissions=set(),
                ),
                sut.ResourceType.ASSET,
            ),
        ]
    ) == repr(resources)

@pytest.mark.integration_test
@pytest.mark.parametrize('asset,agent', [
    pytest.param(
        FunctionResource(
            public_id='assetpubid01',
            name='Asset',
            custom_properties={},
            permissions=set(),
        ),
        FunctionResource(
            public_id='agentpubid01',
            name='Agent',
            custom_properties={},
            permissions=set(),
        ),
        id='with-linked-agent',
    ),
    pytest.param(
        FunctionResource(
            public_id='assetpubid01',
            name='Asset',
            custom_properties={},
            permissions={'MANAGE_AGENT'},
        ),
        None,
        id='without-linked-agent',
    ),
])
@pytest.mark.parametrize('asset_perms,company_perms', [
    pytest.param({'MANAGE_AGENT'}, {}, id='manage-agent'),
    pytest.param({'COMPANY_ADMIN'}, {'COMPANY_ADMIN'}, id='company-admin'),
])
@pytest.mark.parametrize('mut', [
    sut.authorize_upload,
    sut.authorize_update,
    sut.authorize_download,
    sut.authorize_delete,
])
def test_authorize_asset_integration(
        mut: Callable[[FunctionContext], PathResponse],
        asset: FunctionResource,
        agent: FunctionResource,
        asset_perms: set[str],
        company_perms: set[str],
    ):
    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)

    context.company.permissions = company_perms
    context.asset = asset
    context.asset.permissions = asset_perms
    context.agent = agent

    output = mut(context)

    assert {
        "result": "success",
        "data": {
            "path": "assets/assetpubid01/"
        }
    } == output

@pytest.mark.integration_test
@pytest.mark.parametrize('mut', [
    sut.authorize_upload,
    sut.authorize_delete,
])
def test_authorize_upload_delete_asset_no_permission_integration(
        mut: Callable[[FunctionContext], PathResponse],
    ):
    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)

    context.asset = FunctionResource(
        public_id='assetpubid01',
        name='Asset',
        custom_properties={},
        permissions=set(),
    )
    context.agent = FunctionResource(
        public_id='agentpubid01',
        name='Agent',
        custom_properties={},
        permissions=set(),
    )
    context.company = FunctionResource(
        public_id='',
        name='Company',
        custom_properties={},
        permissions=set()
    )

    output = mut(context)

    assert None is output

@pytest.mark.integration_test
@pytest.mark.parametrize('agent_perms,company_perms', [
    pytest.param({'MANAGE_AGENT'}, {}, id='manage-agent'),
    pytest.param({'COMPANY_ADMIN'}, {'COMPANY_ADMIN'}, id='company-admin'),
])
def test_authorize_list_agent_integration(
        agent_perms: set[str], company_perms: set[str]
    ):
    mut = sut.authorize_list

    context = mock.create_autospec(spec=FunctionContext, spec_set=True, instance=True)
    context.company.permissions = company_perms
    context.asset = None
    context.agent.public_id = 'agentpubid01'
    context.agent.permissions = agent_perms

    output = mut(context)

    assert {
        "result": "success",
        "data": [
            {
                "publicId": "agentpubid01",
                "type": "Agent",
                "path": "agents/agentpubid01/",
            },
        ],
    } == output

@pytest.mark.integration_test
def test_authorize_list_asset_with_linked_agent_integration():
    mut = sut.authorize_list

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.api_client = mock.create_autospec(spec=ApiClient, instance=True)

    context.asset.public_id = 'assetpubid01'
    context.agent.public_id = 'agentpubid01'

    output = mut(context)

    assert {
        "result": "success",
        "data": [
            {
                "publicId": "assetpubid01",
                "type": "Asset",
                "path": "assets/assetpubid01/",
            },
            {
                "publicId": "agentpubid01",
                "type": "Agent",
                "path": "agents/agentpubid01/",
            },
        ],
    } == output

@pytest.mark.integration_test
def test_authorize_list_asset_without_linked_agent_integration():
    mut = sut.authorize_list

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.api_client = mock.create_autospec(spec=ApiClient, instance=True)

    context.asset.public_id = 'assetpubid01'
    context.agent = None

    output = mut(context)

    assert output is not None

    assert {
        "result": "success",
        "data": [
            {
                "publicId": "assetpubid01",
                "type": "Asset",
                "path": "assets/assetpubid01/",
            },
        ],
    } == output

@pytest.mark.integration_test
def test_authorize_list_asset_with_other_assets():
    mut = sut.authorize_list

    context = mock.create_autospec(spec=FunctionContext, instance=True)
    context.api_client = mock.create_autospec(spec=ApiClient, instance=True)

    context.asset.public_id = "assetpubid01"
    context.agent = None
    context.api_client.get.return_value = {
        "data": [{"publicId": "assetpubid02", "name": "Asset"}]
    }

    output = mut(context)

    assert {
        "result": "success",
        "data": [
            {
                "publicId": "assetpubid01",
                "type": "Asset",
                "path": "assets/assetpubid01/",
            },
            {
                "publicId": "assetpubid02",
                "type": "Asset",
                "path": "assets/assetpubid02/",
            },
        ],
    } == output
