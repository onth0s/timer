Feature: Countdown display rendering
  As a timer user
  I want the time shown in the correct MM:SS or HH:MM:SS format
  So that I can read the current time at a glance

  Scenario Outline: Countdown display format
    Given the timer is counting down from <seconds> seconds
    When the display renders at second <at_second>
    Then the rendered time string should be "<expected>"

    Examples:
      | seconds | at_second | expected |
      | 90      | 90        | 01:30    |
      | 90      | 60        | 01:00    |
      | 90      | 0         | 00:00    |
      | 3661    | 3661      | 01:01:01 |
      | 3661    | 3600      | 01:00:00 |
      | 3661    | 0         | 00:00:00 |

  Scenario: Display uses MM:SS for durations under 1 hour
    Given the timer is counting down from 90 seconds
    When the display renders at second 90
    Then the format should be MM:SS

  Scenario: Display uses HH:MM:SS when hours component is present
    Given the timer is counting down from 3661 seconds
    When the display renders at second 3661
    Then the format should be HH:MM:SS
