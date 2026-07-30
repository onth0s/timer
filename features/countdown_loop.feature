Feature: Countdown loop logic
  As a developer
  I want the countdown loop to correctly decrement through each second
  Using a mock clock (integer variable, no real sleep) so tests are instant

  Background:
    Given a mock clock starting at 0
    And a mock sleep that increments the clock by the requested amount
    And no real system time is used

  Scenario: Full countdown visits every second in order
    Given a countdown of 5 seconds
    When the countdown loop runs to completion
    Then the seconds displayed should be [5, 4, 3, 2, 1, 0] in order

  Scenario: Countdown stops at zero and does not go negative
    Given a countdown of 3 seconds
    When the countdown loop runs to completion
    Then the minimum displayed value should be 0

  Scenario: Quit key exits the loop before countdown reaches zero
    Given a countdown of 10 seconds
    And a keypress of "q" is queued at second 8
    When the countdown loop runs
    Then the loop exits before reaching 0

  Scenario: Pause halts countdown time while paused
    Given a countdown of 5 seconds
    And a pause keypress is queued at second 4
    And a resume keypress is queued after the equivalent of 3 fake seconds
    When the countdown loop runs to completion
    Then the seconds displayed should still reach 0

  Scenario: Adding time extends the deadline
    Given a countdown of 5 seconds
    And a "+" keypress is queued at second 4
    When the countdown loop runs to completion
    Then the total seconds displayed should be more than 5

  Scenario: Subtracting time shortens the deadline
    Given a countdown of 60 seconds
    And a "-" keypress is queued at second 59
    When the countdown loop runs to completion
    Then the countdown should end sooner than 60 seconds from start
