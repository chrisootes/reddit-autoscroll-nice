

import logging

from nicegui import ui

import reddit

logging.basicConfig(filename='../reddit.log', level=logging.INFO)
logger = logging.getLogger(__name__)

posts = []
posts_index = 0

async def root():
    # Video and image player
    video = ui.video(
        src='5-seconds-of-silence.mp3',
        controls=True,
        autoplay=True
    ).classes('h-full w-full max-h-dvh')

    # Top row buttons
    with ui.grid(columns=7).classes('w-full'):
        ui.button('Reset', icon='start', on_click=lambda: update_post(0))
        ui.button('Previous', icon='arrow_back', on_click=lambda: update_post(-1))
        ui.button('Next', icon='arrow_forward', on_click=lambda: update_post(1))
        multis_list = await reddit.multis()
        multis = ui.select(['front']+multis_list, value='front')
        time = ui.select(['hour', 'day', 'week', 'month', 'year', 'all'], value='all')
        sort = ui.select(['best', 'hot', 'top', 'new', 'rising'], value='best')
        limit = ui.number(label='limit', value=25, format='%d')

    # Post info links
    comments = ui.link()
    subreddit = ui.link()
    user = ui.link()
    score = ui.link()
    created = ui.link()
    selected = ui.link()
    status = ui.link()

    async def update_post(amount):
        """
        callback function for updating the image or video based on the current post index and the amount to change the index by.
        """
        global posts_index
        # Amount is -1 for previous, 1 for next, 0 for initial load or waiting for new posts to load
        posts_index += amount
        # Reset
        if amount == 0:
            posts.clear()
            posts_index = 0
        # First run, download posts if posts list is empty
        if len(posts) == 0:
            new_posts = await reddit.download_posts(sort=sort.value, time=time.value, multis=multis.value, limit=int(limit.value))
            if new_posts is None:
                ui.notify('Failed to download posts!')
                return
            posts.extend(new_posts)
        # Check if posts_index is out of bounds
        if posts_index >= len(posts):
            # Just wait and try again in 2 seconds
            ui.timer(2.0, lambda: update_post(0), once=True)
            ui.notify('Still loading!')
            return
        # Get post corresponding to the current index
        current = posts[posts_index]
        logger.info(f"posts_index={posts_index}, current_post={current}")
        # Update image
        if current['direct_url'] == './audio/5-seconds-of-silence.mp3':
            video.props.update(poster=current['direct_poster'])
            video.set_source('5-seconds-of-silence.mp3')
            video.seek(0)
            video.play()
        # Update video
        else:
            video.set_source(current['direct_url'])
        # Update post info links
        comments.props.update(href=f"https://old.reddit.com/comments/{current['post_id']}")
        comments.set_text(f"Comments: {current['post_title']}")
        subreddit.props.update(href=f"https://old.reddit.com/r/{current['subreddit_name']}")
        subreddit.set_text(f"Subreddit: {current['subreddit_name']}")
        user.props.update(href=f"https://old.reddit.com/u/{current['user_name']}")
        user.set_text(f"User: {current['user_name']}")
        score.set_text(f"Score: {current['post_score']}")
        created.set_text(f"Created: {current['post_created_utc']}")
        selected.set_text(f"Sort: {sort.value}, Time: {time.value}, Multis: {multis.value}")
        status.set_text(f"Status: {posts_index+1}/{len(posts)}")
        # Check if we need to download more posts
        if (posts_index + 1) >= len(posts):
            new_posts = await reddit.download_posts(after=current['post_id'], sort=sort.value, time=time.value, multis=multis.value, limit=limit.value)
            if new_posts is None:
                ui.notify('Failed to download posts!')
                return
            posts.extend(new_posts)

    video.on('loadeddata', video.play)
    video.on('ended', lambda: update_post(1))

ui.run(root)