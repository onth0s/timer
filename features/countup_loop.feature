Feature: Count-up loop logic
  As a developer
  I want the count-up (stopwatch) loop to correctly increment each second
  Using a mock clock (integer variable, no real sleep) so tests are instant

  Background:
    Given a mock clock starting at 0
    And a mock sleep that increments the clock by the requested amount
    And no real system time is used

  Scenario: Stopwatch increments one second per tick
    Given the stopwatch is running
    And a quit keypress is queued after 5 ticks
    When the count-up loop runs
    Then the seconds displayed should be [0, 1, 2, 3, 4, 5] in order

  Scenario: Quit key exits and records elapsed time
    Given the stopwatch is running
    And a quit keypress is queued after 3 ticks
    When the count-up loop runs
    Then the final recorded elapsed time should be 3

  Scenario: Count-up summary message includes elapsed time
    Given the stopwatch ran for 65 seconds then quit
    When the summary is printed
    Then the output should contain "1m5s"
