"""
Flappy Bird clone built with Kivy.
Uses the classic sourabhv/FlappyBirdAssets sprite/audio set.
"""
import random

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Rectangle, Color, PushMatrix, PopMatrix, Rotate
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty
from kivy.core.image import Image as CoreImage

# ---------------------------------------------------------------------------
# Base game design resolution (matches the original sprite sheet proportions)
# ---------------------------------------------------------------------------
BASE_W = 288
BASE_H = 512

GRAVITY = 1400.0          # px/s^2 at design resolution
FLAP_STRENGTH = -380.0    # px/s impulse at design resolution
PIPE_GAP = 130
PIPE_SPACING = 170
PIPE_SPEED = 130.0        # px/s
BASE_SPEED = 130.0
BIRD_X = 60
BIRD_SIZE = (34, 24)

STATE_READY = "ready"
STATE_PLAYING = "playing"
STATE_DEAD = "dead"


def asset(path):
    return "assets/sprites/" + path


def sound(path):
    s = SoundLoader.load("assets/audio/" + path)
    return s


class Bird(Widget):
    velocity = NumericProperty(0)
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.frames = [
            asset("yellowbird-upflap.png"),
            asset("yellowbird-midflap.png"),
            asset("yellowbird-downflap.png"),
        ]
        self.frame_index = 0
        self.anim_time = 0
        self.size = BIRD_SIZE
        self.texture = CoreImage(self.frames[1]).texture
        with self.canvas:
            PushMatrix()
            self.rot = Rotate(angle=0, origin=self.center)
            Color(1, 1, 1, 1)
            self.rect = Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()
        self.bind(pos=self._update, size=self._update, angle=self._update_angle)

    def _update(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.rot.origin = self.center

    def _update_angle(self, *args):
        self.rot.angle = self.angle

    def animate(self, dt):
        self.anim_time += dt
        if self.anim_time > 0.1:
            self.anim_time = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.texture = CoreImage(self.frames[self.frame_index]).texture
            self.rect.texture = self.texture

    def reset(self, x, y):
        self.pos = (x, y)
        self.velocity = 0
        self.angle = 0
        self.frame_index = 1
        self.texture = CoreImage(self.frames[1]).texture
        self.rect.texture = self.texture


class Pipe:
    """A top/bottom pipe pair, drawn manually (not a Widget, for speed)."""

    def __init__(self, canvas_group, texture, x, gap_center, gap, scale):
        self.texture = texture
        tw, th = texture.size
        self.w = tw * scale
        self.h = th * scale
        self.gap = gap
        self.scale = scale
        self.x = x
        self.gap_center = gap_center
        self.scored = False

        with canvas_group:
            Color(1, 1, 1, 1)
            # bottom pipe (normal orientation)
            self.bottom_rect = Rectangle(texture=texture, pos=(x, 0), size=(self.w, self.h))
            # top pipe (flipped vertically) - negative-size trick, no texture-region API needed
            self.top_rect = Rectangle(texture=texture, pos=(x, 0), size=(self.w, -self.h))
        self.set_positions()

    def set_positions(self):
        bottom_y = self.gap_center - self.gap / 2 - self.h
        top_y = self.gap_center + self.gap / 2
        self.bottom_rect.pos = (self.x, bottom_y)
        self.bottom_rect.size = (self.w, self.h)
        # Negative height flips the texture; anchor pos at the TOP of the
        # visual box (top_y + h) so the box still occupies [top_y, top_y+h].
        self.top_rect.pos = (self.x, top_y + self.h)
        self.top_rect.size = (self.w, -self.h)

    def move(self, dx):
        self.x += dx
        self.set_positions()

    def remove(self, canvas_group):
        canvas_group.remove(self.bottom_rect)
        canvas_group.remove(self.top_rect)

    def get_rects(self):
        bottom_y = self.gap_center - self.gap / 2 - self.h
        top_y = self.gap_center + self.gap / 2
        return [
            (self.x, bottom_y, self.w, self.h),
            (self.x, top_y, self.w, self.h),
        ]


class GameWidget(FloatLayout):
    score = NumericProperty(0)
    best_score = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scale = 1.0
        self.state = STATE_READY

        # sounds
        self.snd_wing = sound("wing.wav")
        self.snd_point = sound("point.wav")
        self.snd_hit = sound("hit.wav")
        self.snd_die = sound("die.wav")
        self.snd_swoosh = sound("swoosh.wav")

        # textures
        self.bg_texture = CoreImage(asset("background-day.png")).texture
        self.base_texture = CoreImage(asset("base.png")).texture
        self.pipe_texture = CoreImage(asset("pipe-green.png")).texture
        self.message_texture = CoreImage(asset("message.png")).texture
        self.gameover_texture = CoreImage(asset("gameover.png")).texture
        self.digit_textures = [CoreImage(asset(f"{i}.png")).texture for i in range(10)]

        self.base_scroll = 0.0
        self.bg_scroll = 0.0
        self.pipes = []
        self.pipe_group = self.canvas.before

        with self.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect1 = Rectangle(texture=self.bg_texture)
            self.bg_rect2 = Rectangle(texture=self.bg_texture)

        self.pipes_canvas = Widget(size_hint=(None, None), size=(0, 0))
        self.add_widget(self.pipes_canvas)

        with self.canvas.after:
            Color(1, 1, 1, 1)
            self.base_rect1 = Rectangle(texture=self.base_texture)
            self.base_rect2 = Rectangle(texture=self.base_texture)

        self.bird = Bird()
        self.add_widget(self.bird)

        # UI overlays drawn with canvas.after too (score, message, gameover)
        with self.canvas.after:
            Color(1, 1, 1, 1)
            self.message_rect = Rectangle(texture=self.message_texture)
            self.gameover_rect = Rectangle(texture=self.gameover_texture)
        self.digit_rects = []

        self.playagain_label = Label(
            text="Tap to Play Again",
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            opacity=0,
        )
        self.add_widget(self.playagain_label)

        self.bind(size=self.on_resize, pos=self.on_resize)
        Window.bind(on_key_down=self.on_key_down)

        Clock.schedule_interval(self.update, 1 / 60.0)
        self.reset_game()

    # ------------------------------------------------------------------
    def on_resize(self, *args):
        # `max` fills the entire screen (cropping the sides slightly if the
        # device aspect ratio is narrower/wider than the design ratio)
        # instead of `min`, which would letterbox and leave blank bars.
        self.scale = max(self.width / BASE_W, self.height / BASE_H)
        self.design_w = BASE_W * self.scale
        self.design_h = BASE_H * self.scale
        self.offset_x = self.pos[0] + (self.width - self.design_w) / 2
        self.offset_y = self.pos[1] + (self.height - self.design_h) / 2

        bw, bh = self.bg_texture.size
        bg_w = bw * self.scale
        bg_h = bh * self.scale
        self.bg_h = bg_h
        self.bg_w = bg_w
        self.bg_rect1.size = (bg_w, bg_h)
        self.bg_rect2.size = (bg_w, bg_h)
        self.bg_rect1.pos = (self.offset_x, self.offset_y)
        self.bg_rect2.pos = (self.offset_x + bg_w, self.offset_y)

        base_tw, base_th = self.base_texture.size
        self.base_h = base_th * self.scale
        self.base_w = base_tw * self.scale
        self.base_rect1.size = (self.base_w, self.base_h)
        self.base_rect2.size = (self.base_w, self.base_h)
        self.base_rect1.pos = (self.offset_x, self.offset_y)
        self.base_rect2.pos = (self.offset_x + self.base_w, self.offset_y)

        self.ground_y = self.offset_y + self.base_h
        self.sky_top = self.offset_y + self.design_h

        mw, mh = self.message_texture.size
        self._message_natural_size = (mw * self.scale, mh * self.scale)
        self.message_rect.pos = (
            self.offset_x + self.design_w / 2 - mw * self.scale / 2,
            self.offset_y + self.design_h / 2 - mh * self.scale / 2,
        )

        gw, gh = self.gameover_texture.size
        self._gameover_natural_size = (gw * self.scale, gh * self.scale)
        self.gameover_rect.pos = (
            self.offset_x + self.design_w / 2 - gw * self.scale / 2,
            self.offset_y + self.design_h * 0.65 - gh * self.scale / 2,
        )

        self.playagain_label.font_size = 20 * self.scale
        self.playagain_label.size = (self.design_w, 40 * self.scale)
        self.playagain_label.pos = (
            self.offset_x,
            self.offset_y + self.design_h * 0.65 - gh * self.scale / 2 - 40 * self.scale,
        )

        self._apply_overlay_visibility()

        bird_w, bird_h = BIRD_SIZE
        self.bird.size = (bird_w * self.scale, bird_h * self.scale)
        if self.state != STATE_PLAYING:
            self.bird.pos = (
                self.offset_x + self.design_w * 0.3,
                self.offset_y + self.design_h * 0.5,
            )
        self._redraw_pipes_scale()
        self._redraw_score()

    def _apply_overlay_visibility(self):
        """Show the 'get ready' message only when READY, 'game over' only when DEAD.
        Prevents both overlays from ever being visible at the same time."""
        self.message_rect.size = (
            self._message_natural_size if self.state == STATE_READY else (0, 0)
        )
        self.gameover_rect.size = (
            self._gameover_natural_size if self.state == STATE_DEAD else (0, 0)
        )
        self.playagain_label.opacity = 1 if self.state == STATE_DEAD else 0

    # ------------------------------------------------------------------
    def reset_game(self):
        for p in self.pipes:
            p.remove(self.pipes_canvas.canvas)
        self.pipes = []
        self.score = 0
        self.state = STATE_READY
        self.message_rect.texture = self.message_texture
        self.on_resize()
        self.bird.reset(
            self.offset_x + self.design_w * 0.3,
            self.offset_y + self.design_h * 0.5,
        )

    def start_game(self):
        if self.state == STATE_PLAYING:
            return
        if self.state == STATE_DEAD:
            self.reset_game()
        self.state = STATE_PLAYING
        self._apply_overlay_visibility()
        self.spawn_pipes_initial()
        self.flap()

    def flap(self):
        if self.state == STATE_DEAD:
            self.start_game()
            return
        if self.state == STATE_READY:
            self.start_game()
            return
        self.bird.velocity = FLAP_STRENGTH * self.scale
        if self.snd_wing:
            self.snd_wing.play()

    def on_touch_down(self, touch):
        self.flap()
        return True

    def on_key_down(self, window, key, *args):
        if key == 32:  # spacebar
            self.flap()
        return True

    # ------------------------------------------------------------------
    def spawn_pipes_initial(self):
        for p in self.pipes:
            p.remove(self.pipes_canvas.canvas)
        self.pipes = []
        start_x = self.offset_x + self.design_w + 40 * self.scale
        for i in range(4):
            self._add_pipe(start_x + i * PIPE_SPACING * self.scale)

    def _add_pipe(self, x):
        gap_center = random.uniform(
            self.offset_y + self.design_h * 0.3,
            self.offset_y + self.design_h * 0.75,
        )
        pipe = Pipe(
            self.pipes_canvas.canvas,
            self.pipe_texture,
            x,
            gap_center,
            PIPE_GAP * self.scale,
            self.scale,
        )
        self.pipes.append(pipe)

    def _redraw_pipes_scale(self):
        # on resize keep pipes proportionally placed (simplified: just rescale gap width)
        for p in self.pipes:
            p.scale = self.scale
            tw, th = p.texture.size
            p.w = tw * self.scale
            p.h = th * self.scale
            p.gap = PIPE_GAP * self.scale
            p.set_positions()

    # ------------------------------------------------------------------
    def update(self, dt):
        # background & base scroll (always, for idle animation feel)
        self.bg_scroll -= 10 * self.scale * dt
        if self.bg_scroll <= -self.bg_w:
            self.bg_scroll += self.bg_w
        self.bg_rect1.pos = (self.offset_x + self.bg_scroll, self.offset_y)
        self.bg_rect2.pos = (self.offset_x + self.bg_scroll + self.bg_w, self.offset_y)

        if self.state != STATE_DEAD:
            self.base_scroll -= BASE_SPEED * self.scale * dt
            if self.base_scroll <= -self.base_w:
                self.base_scroll += self.base_w
        self.base_rect1.pos = (self.offset_x + self.base_scroll, self.offset_y)
        self.base_rect2.pos = (self.offset_x + self.base_scroll + self.base_w, self.offset_y)

        self.bird.animate(dt)

        if self.state == STATE_READY:
            return

        if self.state == STATE_PLAYING:
            # physics
            self.bird.velocity += GRAVITY * self.scale * dt
            new_y = self.bird.y - self.bird.velocity * dt
            self.bird.y = new_y
            # angle
            target_angle = max(-25, min(90, -self.bird.velocity * 0.08))
            self.bird.angle = target_angle

            # move pipes
            dx = -PIPE_SPEED * self.scale * dt
            for p in self.pipes:
                p.move(dx)

            # score + recycle
            for p in self.pipes:
                if not p.scored and p.x + p.w < self.bird.x:
                    p.scored = True
                    self.score += 1
                    if self.snd_point:
                        self.snd_point.play()

            if self.pipes and self.pipes[0].x + self.pipes[0].w < self.offset_x - 20:
                old = self.pipes.pop(0)
                old.remove(self.pipes_canvas.canvas)
                last_x = self.pipes[-1].x if self.pipes else self.offset_x + self.design_w
                self._add_pipe(last_x + PIPE_SPACING * self.scale)

            self._redraw_score()
            self._check_collisions()

        elif self.state == STATE_DEAD:
            if self.bird.y > self.ground_y:
                self.bird.velocity += GRAVITY * self.scale * dt
                self.bird.y -= self.bird.velocity * dt
                self.bird.angle = max(-25, min(90, -self.bird.velocity * 0.08))
            else:
                self.bird.y = self.ground_y
                self.bird.angle = 90

    def _check_collisions(self):
        bx, by = self.bird.pos
        bw, bh = self.bird.size
        # ground / ceiling
        if by <= self.ground_y:
            self.bird.y = self.ground_y
            self._die()
            return
        if by + bh >= self.sky_top:
            self.bird.y = self.sky_top - bh
            self.bird.velocity = 0

        pad = 4 * self.scale
        bird_rect = (bx + pad, by + pad, bw - 2 * pad, bh - 2 * pad)
        for p in self.pipes:
            for (px, py, pw, ph) in p.get_rects():
                if self._overlap(bird_rect, (px, py, pw, ph)):
                    self._die()
                    return

    @staticmethod
    def _overlap(r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    def _die(self):
        if self.state == STATE_DEAD:
            return
        self.state = STATE_DEAD
        self.best_score = max(self.best_score, self.score)
        if self.snd_hit:
            self.snd_hit.play()
        if self.snd_die:
            self.snd_die.play()
        self._apply_overlay_visibility()

    # ------------------------------------------------------------------
    def _redraw_score(self):
        for r in self.digit_rects:
            self.canvas.after.remove(r)
        self.digit_rects = []
        digits = str(self.score)
        dw, dh = self.digit_textures[0].size
        dw *= self.scale
        dh *= self.scale
        spacing = 2 * self.scale
        total_w = len(digits) * dw + (len(digits) - 1) * spacing
        start_x = self.offset_x + self.design_w / 2 - total_w / 2
        y = self.offset_y + self.design_h * 0.85
        with self.canvas.after:
            Color(1, 1, 1, 1)
            for i, ch in enumerate(digits):
                tex = self.digit_textures[int(ch)]
                rect = Rectangle(
                    texture=tex,
                    pos=(start_x + i * (dw + spacing), y),
                    size=(dw, dh),
                )
                self.digit_rects.append(rect)


class FlappyBirdApp(App):
    def build(self):
        Window.clearcolor = (0.53, 0.81, 0.92, 1)
        return GameWidget()


if __name__ == "__main__":
    FlappyBirdApp().run()       self.flap()
        return True

    # ------------------------------------------------------------------
    def spawn_pipes_initial(self):
        for p in self.pipes:
            p.remove(self.pipes_canvas.canvas)
        self.pipes = []
        start_x = self.offset_x + self.design_w + 40 * self.scale
        for i in range(4):
            self._add_pipe(start_x + i * PIPE_SPACING * self.scale)

    def _add_pipe(self, x):
        gap_center = random.uniform(
            self.offset_y + self.design_h * 0.3,
            self.offset_y + self.design_h * 0.75,
        )
        pipe = Pipe(
            self.pipes_canvas.canvas,
            self.pipe_texture,
            x,
            gap_center,
            PIPE_GAP * self.scale,
            self.scale,
        )
        self.pipes.append(pipe)

    def _redraw_pipes_scale(self):
        # on resize keep pipes proportionally placed (simplified: just rescale gap width)
        for p in self.pipes:
            p.scale = self.scale
            tw, th = p.texture.size
            p.w = tw * self.scale
            p.h = th * self.scale
            p.gap = PIPE_GAP * self.scale
            p.set_positions()

    # ------------------------------------------------------------------
    def update(self, dt):
        # background & base scroll (always, for idle animation feel)
        self.bg_scroll -= 10 * self.scale * dt
        if self.bg_scroll <= -self.bg_w:
            self.bg_scroll += self.bg_w
        self.bg_rect1.pos = (self.offset_x + self.bg_scroll, self.offset_y)
        self.bg_rect2.pos = (self.offset_x + self.bg_scroll + self.bg_w, self.offset_y)

        if self.state != STATE_DEAD:
            self.base_scroll -= BASE_SPEED * self.scale * dt
            if self.base_scroll <= -self.base_w:
                self.base_scroll += self.base_w
        self.base_rect1.pos = (self.offset_x + self.base_scroll, self.offset_y)
        self.base_rect2.pos = (self.offset_x + self.base_scroll + self.base_w, self.offset_y)

        self.bird.animate(dt)

        if self.state == STATE_READY:
            return

        if self.state == STATE_PLAYING:
            # physics
            self.bird.velocity += GRAVITY * self.scale * dt
            new_y = self.bird.y - self.bird.velocity * dt
            self.bird.y = new_y
            # angle
            target_angle = max(-25, min(90, -self.bird.velocity * 0.08))
            self.bird.angle = target_angle

            # move pipes
            dx = -PIPE_SPEED * self.scale * dt
            for p in self.pipes:
                p.move(dx)

            # score + recycle
            for p in self.pipes:
                if not p.scored and p.x + p.w < self.bird.x:
                    p.scored = True
                    self.score += 1
                    if self.snd_point:
                        self.snd_point.play()

            if self.pipes and self.pipes[0].x + self.pipes[0].w < self.offset_x - 20:
                old = self.pipes.pop(0)
                old.remove(self.pipes_canvas.canvas)
                last_x = self.pipes[-1].x if self.pipes else self.offset_x + self.design_w
                self._add_pipe(last_x + PIPE_SPACING * self.scale)

            self._redraw_score()
            self._check_collisions()

        elif self.state == STATE_DEAD:
            if self.bird.y > self.ground_y:
                self.bird.velocity += GRAVITY * self.scale * dt
                self.bird.y -= self.bird.velocity * dt
                self.bird.angle = max(-25, min(90, -self.bird.velocity * 0.08))
            else:
                self.bird.y = self.ground_y
                self.bird.angle = 90

    def _check_collisions(self):
        bx, by = self.bird.pos
        bw, bh = self.bird.size
        # ground / ceiling
        if by <= self.ground_y:
            self.bird.y = self.ground_y
            self._die()
            return
        if by + bh >= self.sky_top:
            self.bird.y = self.sky_top - bh
            self.bird.velocity = 0

        pad = 4 * self.scale
        bird_rect = (bx + pad, by + pad, bw - 2 * pad, bh - 2 * pad)
        for p in self.pipes:
            for (px, py, pw, ph) in p.get_rects():
                if self._overlap(bird_rect, (px, py, pw, ph)):
                    self._die()
                    return

    @staticmethod
    def _overlap(r1, r2):
        x1, y1, w1, h1 = r1
        x2, y2, w2, h2 = r2
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2

    def _die(self):
        if self.state == STATE_DEAD:
            return
        self.state = STATE_DEAD
        self.best_score = max(self.best_score, self.score)
        if self.snd_hit:
            self.snd_hit.play()
        if self.snd_die:
            self.snd_die.play()
        gw, gh = self.gameover_texture.size
        self.gameover_rect.size = (gw * self.scale, gh * self.scale)

    # ------------------------------------------------------------------
    def _redraw_score(self):
        for r in self.digit_rects:
            self.canvas.after.remove(r)
        self.digit_rects = []
        digits = str(self.score)
        dw, dh = self.digit_textures[0].size
        dw *= self.scale
        dh *= self.scale
        spacing = 2 * self.scale
        total_w = len(digits) * dw + (len(digits) - 1) * spacing
        start_x = self.offset_x + self.design_w / 2 - total_w / 2
        y = self.offset_y + self.design_h * 0.85
        with self.canvas.after:
            Color(1, 1, 1, 1)
            for i, ch in enumerate(digits):
                tex = self.digit_textures[int(ch)]
                rect = Rectangle(
                    texture=tex,
                    pos=(start_x + i * (dw + spacing), y),
                    size=(dw, dh),
                )
                self.digit_rects.append(rect)


class FlappyBirdApp(App):
    def build(self):
        Window.clearcolor = (0.53, 0.81, 0.92, 1)
        return GameWidget()


if __name__ == "__main__":
    FlappyBirdApp().run()
