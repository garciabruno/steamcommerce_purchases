#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from flask import request
from flask import Blueprint

import json
import time

from core import enums
from tasks import edge as edge_task
from utils import route_decorators

edge = Blueprint('edge.api', __name__)


@edge.route('/healthcheck')
def edge_healthcheck():
    requested_at = request.headers.get('X-Requested-At', time.time())
    now = time.time()

    try:
        diff = now - float(requested_at)
    except ValueError:
        diff = 0

    return str(diff)


@edge.route('/task/state/', methods=['POST'])
@route_decorators.as_json
def edge_cart_status():
    task_id = request.form.get('task_id')
    task_name = request.form.get('task_name')

    if not hasattr(edge_task, task_name):
        return {
            'success': False,
            'result': enums.EdgeResult.TaskNotFound.value
        }

    task = getattr(edge_task, task_name).AsyncResult(task_id)

    try:
        task_result = json.dumps(task.result)
    except ValueError:
        task_result = str(task_result)

    return {
        'success': True,
        'task_status': task.state,
        'task_result': task_result
    }


@edge.route('/cart/push/', methods=['POST'])
@route_decorators.as_json
def edge_cart_push():
    items = request.form.get('items')
    network_id = request.form.get('network_id')

    if not items or not network_id:
        return {
            'success': False,
            'result': enums.EdgeResult.IncompleteForm.value
        }

    try:
        items = json.loads(items)
    except ValueError:
        return {
            'success': False,
            'result': enums.EdgeResult.ParamNotSerializable.value
        }

    try:
        network_id = int(network_id)
    except ValueError:
        return {
            'success': False,
            'result': enums.EdgeResult.ParamNotSerializable.value
        }

    task = edge_task.add_subids_to_cart.delay(network_id, items)

    return {
        'success': True,
        'task_id': task.id,
        'task_status': task.status,
        'task_name': 'add_subids_to_cart'
    }


@edge.route('/cart/checkout/', methods=['POST'])
@route_decorators.as_json
def edge_cart_checkout():
    network_id = request.form.get('network_id')
    giftee_account_id = request.form.get('giftee_account_id')
    payment_method = request.form.get('payment_method') or 'steamaccount'

    try:
        network_id = int(network_id)
    except ValueError:
        return {
            'success': False,
            'result': enums.EdgeResult.ParamNotSerializable.value
        }

    task = edge_task.checkout_cart.delay(network_id, giftee_account_id, payment_method=payment_method)

    return {
        'success': True,
        'task_id': task.id,
        'task_status': task.status,
        'task_name': 'checkout_cart'
    }


@edge.route('/cart/reset/', methods=['POST'])
@route_decorators.as_json
def edge_cart_reset():
    network_id = request.form.get('network_id')

    try:
        network_id = int(network_id)
    except ValueError:
        return {
            'success': False,
            'result': enums.EdgeResult.ParamNotSerializable.value
        }

    task = edge_task.reset_shopping_cart.delay(network_id)

    return {
        'success': True,
        'task_id': task.id,
        'task_status': task.status,
        'task_name': 'reset_shopping_cart'
    }


@edge.route('/transaction/link/', methods=['POST'])
@route_decorators.as_json
def edge_transaction_link():
    transid = request.form.get('transid')
    network_id = request.form.get('network_id')

    if not transid:
        return {
            'succes': False,
            'result': enums.EdgeResult.IncompleteForm.value
        }

    try:
        network_id = int(network_id)
    except ValueError:
        return {
            'success': False,
            'result': enums.EdgeResult.ParamNotSerializable.value
        }

    task = edge_task.get_external_link_from_transid.delay(network_id, transid)

    return {
        'success': True,
        'task_id': task.id,
        'task_status': task.status,
        'task_name': 'get_external_link_from_transid'
    }
