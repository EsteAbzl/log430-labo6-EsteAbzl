"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data # user id et items
        self.total_amount = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            # TODO: effectuer une requête à /orders pour obtenir le total_amount de la commande (que sera utilisé pour démander la transaction de paiement)
            """
            GET my-api-gateway-address/order/{id} ...
            """
            self.logger.debug(f"requete order id...")
            self.logger.debug(f"requete order id : {self.order_id}")
            response = requests.get(f'{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}')
            self.logger.debug(f"requete order id done")
            if response.ok:
                data = response.json() 
                self.total_amount = data['total_amount'] if data else 0
            else:
                text = response.json() 
                self.logger.error(f"Requête total amout a échoué : {response.status_code} - {text}")
                return self.rollback()
            
            
            self.logger.debug(f"total amount = {self.total_amount}")

            # TODO: effectuer une requête à /payments pour créer une transaction de paiement
            """
            POST my-api-gateway-address/payments ...
            json={ voir collection Postman pour en savoir plus ... }
            """
            response = requests.post(f'{config.API_GATEWAY_URL}/payments-api/payments',
                json={
                    "user_id": self.order_data['user_id'],
                    "order_id": self.order_id,
                    "total_amount": self.total_amount
                },
                headers={'Content-Type': 'application/json'}
            )
            if response.ok:
                self.logger.debug("Transition d'état: CreatePayment -> PAYMENT_CREATED")
                return OrderSagaState.PAYMENT_CREATED
            else:
                self.logger.debug("payment demandé mais pas ok")
                return self.rollback()

        except Exception:
            self.logger.debug("problème dans handler payment")
            return self.rollback()
        
    def rollback(self):
        """ Call StoreManager to restore stock quantities if payment transaction creation fails """
        # TODO: remettre en stock tous les articles qui avaient été retirés du stock (dans self.order_data)
        requests.put(f'{config.API_GATEWAY_URL}/store-manager-api/stocks',
                json={
                    "items": self.order_data['items'],
                    "operation": "+"
                },
                headers={'Content-Type': 'application/json'}
            )
        self.logger.debug("Transition d'état: CreatePaymentFailure -> STOCK_INCREASED")
        return OrderSagaState.STOCK_INCREASED