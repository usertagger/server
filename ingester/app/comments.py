import os

import msgpack
import praw
import redis

from logzero import logger, loglevel

from shared import ConfigData

def main(subreddit_list, log_level):
    config = ConfigData()
    loglevel(log_level)
    redis_client = redis.Redis(host="redis")
    reddit = praw.Reddit(user_agent=f"Ingester by /u/{config.username}", client_id=config.client_id, client_secret=config.secret_id, username=config.username, password=config.password)

    subreddit_combo = reddit.subreddit(subreddit_list)

    for comment in subreddit_combo.stream.comments():
        attrs = vars(comment)
        logger.debug(f"Received new comment: {attrs}")
        try:
            process_comment(comment, redis_client)
        except Exception as e:
            logger.exception(e)
            raise e

def process_comment(comment, redis_client):
    if not comment.author: # API edge case... this happens sometimes
        return

    stored_data = redis_client.get(comment.author.name)
    if stored_data:
        stored_data = msgpack.unpackb(stored_data)
    else:
        stored_data = {
            "submissions": {
                # {
                    # "subredditname": [
                        # "linkid"
                    # ]
                # }
            },
            "comments": {
                # {
                    # "subredditname": [
                        # "linkid"
                    # ]
                # }
            }
        }

    if comments_list := stored_data["comments"].get(comment.subreddit_name_prefixed):
        if comment.id not in comments_list:
            comments_list.append(comment.id)
    else:
        stored_data["comments"][comment.subreddit_name_prefixed] = [comment.id]
    redis_client.set(comment.author.name, msgpack.packb(stored_data))

if __name__ == "__main__":
    main(os.environ["SUBREDDITS"], os.environ["LOGLEVEL"])