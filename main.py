

import logging

from nicegui import ui

import reddit

logging.basicConfig(filename='../reddit.log', level=logging.INFO)
logger = logging.getLogger(__name__)

class App:
    def __init__(self):
        self.posts = []
        self.posts_index = 0

        # Video and image player
        self.video = ui.video(
            src='5-seconds-of-silence.mp3',
            controls=True,
            autoplay=True
        ).classes('h-full w-full max-h-dvh')
        self.video.on('loadeddata', self.video.play)
        self.video.on('ended', lambda: self.update_post(1))

        # Top row buttons
        with ui.grid(columns=7).classes('w-full'):
            ui.button('Reset', icon='start', on_click=lambda: self.update_post(0))
            ui.button('Previous', icon='arrow_back', on_click=lambda: self.update_post(-1))
            ui.button('Next', icon='arrow_forward', on_click=lambda: self.update_post(1))
            multis_list = reddit.multis()
            self.multis = ui.select(['front']+multis_list, value='front')
            self.time = ui.select(['hour', 'day', 'week', 'month', 'year', 'all'], value='all')
            self.sort = ui.select(['best', 'hot', 'top', 'new', 'rising'], value='best')
            self.limit = ui.number(label='limit', value=25, format='%d')

        # Post info links
        self.comments = ui.link()
        self.subreddit = ui.link()
        self.user = ui.link()
        self.score = ui.link()
        self.created = ui.link()
        self.selected = ui.link()
        self.status = ui.link()

    async def update_post(self, amount):
        """
        callback function for updating the image or video based on the current post index and the amount to change the index by.
        """
        # Amount is -1 for previous, 1 for next, 0 for initial load or waiting for new posts to load
        self.posts_index += amount
        # Reset
        if amount == 0:
            self.posts.clear()
            self.posts_index = 0
        # First run, download posts if posts list is empty
        if len(self.posts) == 0:
            # TODO for
            new_posts = await reddit.download_posts(sort=self.sort.value, time=self.time.value, multis=self.multis.value, limit=int(self.limit.value or 20))
            if new_posts is None:
                ui.notify('Failed to download posts!')
                return
            self.posts.extend(new_posts)
        # Check if posts_index is out of bounds
        if self.posts_index >= len(self.posts):
            # Just wait and try again in 2 seconds
            ui.timer(2.0, lambda: self.update_post(0), once=True)
            ui.notify('Still loading!')
            return
        # Get post corresponding to the current index
        current = self.posts[self.posts_index]
        logger.info(f"posts_index={self.posts_index}, current_post={current}")
        # Update image
        if current['direct_url'] == './audio/5-seconds-of-silence.mp3':
            self.video.props.update(poster=current['direct_poster'])
            self.video.set_source('5-seconds-of-silence.mp3')
            self.video.seek(0)
            self.video.play()
        # Update video
        else:
            self.video.set_source(current['direct_url'])
        # Update post info links
        self.comments.props.update(href=f"https://old.reddit.com/comments/{current['post_id']}")
        self.comments.set_text(f"Comments: {current['post_title']}")
        self.subreddit.props.update(href=f"https://old.reddit.com/r/{current['subreddit_name']}")
        self.subreddit.set_text(f"Subreddit: {current['subreddit_name']}")
        self.user.props.update(href=f"https://old.reddit.com/u/{current['user_name']}")
        self.user.set_text(f"User: {current['user_name']}")
        self.score.set_text(f"Score: {current['post_score']}")
        self.created.set_text(f"Created: {current['post_created_utc']}")
        self.selected.set_text(f"Sort: {self.sort.value}, Time: {self.time.value}, Multis: {self.multis.value}")
        self.status.set_text(f"Status: {self.posts_index+1}/{len(self.posts)}")
        # Check if we need to download more posts
        if (self.posts_index + 1) >= len(self.posts):
            new_posts = await reddit.download_posts(after=current['post_name'], sort=self.sort.value, time=self.time.value, multis=self.multis.value, limit=int(self.limit.value or 20))
            if new_posts is None:
                ui.notify('Failed to download posts!')
                return
            self.posts.extend(new_posts)

@ui.page("/")
def main():
    app = App()

ui.run()