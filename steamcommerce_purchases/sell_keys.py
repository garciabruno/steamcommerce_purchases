import sys

import bot
import controller

if len(sys.argv) == 3:
    market_hash_name = sys.argv[1]
    amount = int(sys.argv[2])

    bot_obj = controller.BotController().get_first_active_bot()
    pb = bot.get_purchasebot(bot_obj)

    pb.sell_items_to_market(market_hash_name, amount)

