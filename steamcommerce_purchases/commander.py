#!/usr/bin/env python
# -*- coding:Utf-8 -*-


from steamcommerce_api.core import models

from steamcommerce_api.api import logger
from steamcommerce_api.api import userrequest
from steamcommerce_api.api import paidrequest

import enums
import config

log = logger.Logger('SteamCommerce Commander', 'commander.log').get_logger()


class Commander(object):
    def __init__(self):
        self.userrequest_relation = models.ProductUserRequestRelation
        self.paidrequest_relation = models.ProductPaidRequestRelation

        self.ADMIN_ID = config.ADMIN_ID

    def get_commited_store_subids(self):
        userrequests = userrequest.UserRequest().get_paid()
        paidrequests = paidrequest.PaidRequest().get_paid()

        subids = []

        for userrequest_data in userrequests:
            for relation in userrequest_data.get('userrequest_relations'):
                if (
                    relation.get('product').get('store_sub_id') or
                    relation.get('product').get('sub_id') and
                    relation.get('commitment_level') ==
                    enums.ECommitLevel.AddedToCart and not
                    relation.get('sent')
                ):
                    subids.append(
                        relation.get('product').get('store_sub_id') or
                        relation.get('product').get('sub_id')
                    )

        for paidrequest_data in paidrequests:
            for relation in paidrequest_data.get('paidrequest_relations'):
                if (
                    relation.get('product').get('store_sub_id') or
                    relation.get('product').get('sub_id') and
                    relation.get('commitment_level') ==
                    enums.ECommitLevel.AddedToCart and not
                    relation.get('sent')
                ):
                    subids.append(
                        relation.get('product').get('store_sub_id') or
                        relation.get('product').get('sub_id')
                    )

        return subids

    def get_pending_userrequest_relations(self):
        relations = self.userrequest_relation.select().join(
            models.UserRequest
        ).where(
            models.UserRequest.paid == True,
            models.UserRequest.visible == True,
            models.UserRequest.accepted == False,
            (models.UserRequest.assigned == None) |
            (models.UserRequest.assigned == self.ADMIN_ID),
            self.userrequest_relation.commitment_level ==
            enums.ECommitLevel.Uncommited.value
        )

        commited_store_subids = self.get_commited_store_subids()

        log.info(
            u'Found {0} pending userrequest relations'.format(
                relations.count()
            )
        )

        results = {}

        for relation in relations:
            currency = relation.product.price_currency

            if not currency:
                continue

            if not currency in results.keys():
                results[currency] = []

            if (
                not relation.product.store_sub_id and
                not relation.product.sub_id
            ):
                log.error(
                    u'Product id {0} did not contain sub id'.format(
                        relation.product.id
                    )
                )

                # TODO: Call task for relation.product.id ?

                continue

            if (
                relation.product.store_sub_id in commited_store_subids or
                relation.product.sub_id in commited_store_subids
            ):
                continue

            results[currency].append({
                'relation_type': 1,
                'relation_id': relation.id,
                'subid': int(
                    relation.product.store_sub_id or relation.product.sub_id
                ),
            })

        return results

    def get_pending_paidrequest_relations(self):
        relations = self.paidrequest_relation.select().join(
            models.PaidRequest
        ).where(
            models.PaidRequest.authed == True,
            models.PaidRequest.visible == True,
            models.PaidRequest.accepted == False,
            (models.PaidRequest.assigned == None) |
            (models.PaidRequest.assigned == self.ADMIN_ID),
            self.paidrequest_relation.commitment_level ==
            enums.ECommitLevel.Uncommited.value
        )

        commited_store_subids = self.get_commited_store_subids()

        log.info(
            u'Found {0} pending paidrequest relations'.format(
                relations.count()
            )
        )

        results = {}

        for relation in relations:
            currency = relation.product.price_currency

            if not currency:
                continue

            if not currency in results.keys():
                results[currency] = []

            if (
                not relation.product.store_sub_id and
                not relation.product.sub_id
            ):
                log.error(
                    u'Product id {0} did not contain sub id'.format(
                        relation.product.id
                    )
                )

                # TODO: Call task for relation.product.id ?

                continue

            if (
                relation.product.store_sub_id in commited_store_subids or
                relation.product.sub_id in commited_store_subids
            ):
                continue

            results[currency].append({
                'relation_type': 2,
                'relation_id': relation.id,
                'subid': int(
                    relation.product.store_sub_id or relation.product.sub_id
                ),
            })

        return results

    def get_pending_relations(self):
        log.info(u'Getting pending relations for bots')

        userrequest_results = self.get_pending_userrequest_relations()
        paidrequest_results = self.get_pending_paidrequest_relations()

        results = {}

        # Merge userrequest and paidrequest relations together

        for currency in userrequest_results.keys():
            if not currency in results.keys():
                results[currency] = []

            results[currency] = (
                results[currency] + userrequest_results[currency]
            )

        for currency in paidrequest_results.keys():
            if not currency in results.keys():
                results[currency] = []

            results[currency] = (
                results[currency] + paidrequest_results[currency]
            )

        # Filter out repeated subids so we don't push them twice to the bots

        seen_subs = []

        for currency in results.keys():
            for item in results[currency]:
                if item['subid'] not in seen_subs:
                    seen_subs.append(item['subid'])
                else:
                    # We already have this subid in the results, filter it

                    results[currency] = filter(
                        lambda x: (
                            x['subid'] != item['subid']
                        ),
                        results[currency]
                    )

                    # We filtered out *all* subids like that one, now re-add it

                    results[currency].append(item)

        return results

    def process_bot_results(self, results):
        log.info(u'Processing results from bot id {0}'.format(results['id']))

        for item in results.get('items'):
            if item.get('relation_type') == 1:
                log.info(
                    u'Commiting UserRequest relation id {0}'.format(
                        item.get('relation_id')
                    )
                )

                userrequest.UserRequest().set_commitment(
                    item.get('relation_id'),
                    enums.ECommitLevel.AddedToCart.value,
                    results['id'],
                    shopping_cart_gid=item.get('shoppingCartGid')
                )

                request_id = self.userrequest_relation.get(
                    id=item.get('relation_id')
                ).request_id

                log.info(
                    u'Assigning admin to UserRequest id {0}'.format(
                        request_id
                    )
                )

                userrequest.UserRequest().assign(
                    request_id,
                    config.ADMIN_ID
                )
            elif item.get('relation_type') == 2:
                log.info(
                    u'Commiting PaidRequest relation id {0}'.format(
                        item.get('relation_id')
                    )
                )

                paidrequest.PaidRequest().set_commitment(
                    item.get('relation_id'),
                    enums.ECommitLevel.AddedToCart.value,
                    results['id'],
                    shopping_cart_gid=item.get('shoppingCartGid')
                )

                request_id = self.paidrequest_relation.get(
                    id=item.get('relation_id')
                ).request_id

                log.info(
                    u'Assigning admin to PaidRequest id {0}'.format(
                        request_id
                    )
                )

                paidrequest.PaidRequest().assign(
                    request_id,
                    config.ADMIN_ID
                )

        if not 'failed_gids' in results.keys():
            return results

        log.info(
            u'Received a list of previously commited shoppingCartGids'
        )

        for failed_gid in results['failed_gids']:
            log.info(
                u'Rolling back relations with shoppingCartGid {0}'.format(
                    failed_gid
                )
            )

            self.userrequest_relation.update(
                commited_on_bot=None,
                shopping_cart_gid=None,
                commitment_level=enums.ECommitLevel.Uncommited.value,
            ).where(
                self.userrequest_relation.shopping_cart_gid == failed_gid,
                self.userrequest_relation.commitment_level ==
                enums.ECommitLevel.AddedToCart.value,
                self.userrequest_relation.sent == False
            ).execute()

            self.paidrequest_relation.update(
                commited_on_bot=None,
                shopping_cart_gid=None,
                commitment_level=enums.ECommitLevel.Uncommited.value
            ).where(
                self.paidrequest_relation.shopping_cart_gid == failed_gid,
                self.paidrequest_relation.commitment_level ==
                enums.ECommitLevel.AddedToCart.value,
                self.paidrequest_relation.sent == False
            ).execute()

            userrequest.UserRequest().flush_relations()
            paidrequest.PaidRequest().flush_relations()

        return results
