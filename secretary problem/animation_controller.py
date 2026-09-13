from typing import Callable, Optional
from simulation import TrialResult, CandidateEvent

class AnimationController:
    """ Steps through a TrialResult's history over time using Tkinter's widget.after() scheduling """

    def __init__( self, widget, on_step: Callable[[CandidateEvent, int, int], None], on_complete: Optional[Callable[[TrialResult], None]] = None, step_delay_ms: int = 600,):
        self._widget = widget
        self._on_step = on_step # called per revealed candidate
        self._on_complete = on_complete # called once after last candidate revealed
        self.step_delay_ms = step_delay_ms

        self._trial: Optional[TrialResult] = None
        self._current_index = 0
        self._after_id = None
        self._is_playing = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_finished(self) -> bool:
        return (self._trial is not None and self._current_index >= len(self._trial.history))

    def load_trial(self, trial: TrialResult) -> None:
        """ Load new trial to animate """
        self.stop()

        self._trial = trial
        self._current_index = 0

    def set_speed(self, step_delay_ms: int) -> None:
        """ Change the delay between steps """
        self.step_delay_ms = step_delay_ms

    def play(self) -> None:
        """ Start (or resume) playback from the current position """
        if self._trial is None or self._is_playing:
            return

        self._is_playing = True
        self._schedule_next_step(immediate=True)

    def pause(self) -> None:
        """ Pause playback without resetting position """
        self._is_playing = False
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def stop(self) -> None:
        """ Pause playback AND reset position back to the beginning """
        self.pause()
        self._current_index = 0

    def step_once(self) -> None:
        """ Manually reveal a single candidate """
        if self._is_playing or self._trial is None:
            return
        self._advance_one_step()

    def _schedule_next_step(self, immediate: bool = False) -> None:
        delay = 0 if immediate else self.step_delay_ms
        self._after_id = self._widget.after(delay, self._advance_one_step)

    def _advance_one_step(self) -> None:
        if self._trial is None:
            return

        total = len(self._trial.history)

        if self._current_index >= total:
            self._is_playing = False
            if self._on_complete:
                self._on_complete(self._trial)
            return

        event = self._trial.history[self._current_index]
        self._on_step(event, self._current_index, total)
        self._current_index += 1

        if self._current_index >= total:
            self._is_playing = False
            if self._on_complete:
                self._on_complete(self._trial)
        elif self._is_playing:
            self._schedule_next_step()