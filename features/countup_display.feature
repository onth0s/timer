Feature: Count-up display rendering
  As a timer user running the stopwatch (no duration argument)
  I want the display to show seconds-only below 60s, then MM:SS, then HH:MM:SS
  So the format grows naturally as time passes

  Scenario Outline: Count-up display format progression
    Given the stopwatch has been running for <elapsed> seconds
    When the display renders
    Then the rendered time string should be "<expected>"

    Examples:
      | elapsed | expected |
      | 0       | 00       |
      | 1       | 01       |
      | 59      | 59       |
      | 60      | 01:00    |
      | 61      | 01:01    |
      | 3599    | 59:59    |
      | 3600    | 01:00:00 |
      | 3601    | 01:00:01 |
