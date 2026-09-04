Feature: Full-Screen Digital Clock
  The user can run a full-screen live wall clock using terminal glyphs,
  with configurable 12/24h format, seconds, date, and interactive controls.

  Scenario: Clock runs and quits cleanly on 'q'
    Given a mock clock starting at timestamp 1788523530
    And a quit keypress is queued at tick 1
    When the clock loop is executed
    Then the clock ran for 1 second
    And the clock summary is displayed

  Scenario: Cannot specify both --twelve and --twenty-four
    Given the clock CLI is invoked with "--twelve --twenty-four"
    When the CLI command completes
    Then the exit code should not be 0
    And the output should contain "Cannot specify both --twelve and --twenty-four"

  Scenario: 24-hour formatting with and without seconds
    Given a datetime at 14:25:30
    When formatted in 24-hour mode with seconds
    Then the time string should be "14:25:30"
    And the ampm string should be none
    When formatted in 24-hour mode without seconds
    Then the time string should be "14:25"
    And the ampm string should be none

  Scenario: 12-hour formatting with AM and PM
    Given a datetime at 14:25:30
    When formatted in 12-hour mode with seconds
    Then the time string should be "02:25:30"
    And the ampm string should be "PM"
    Given a datetime at 09:05:01
    When formatted in 12-hour mode without seconds
    Then the time string should be "09:05"
    And the ampm string should be "AM"

  Scenario: Date formatting
    Given a datetime on 2026-09-04
    When the clock date is formatted
    Then the date string should be "Friday, September 4, 2026"

  Scenario: Interactive key toggle for seconds
    Given a mock clock starting at timestamp 1788523530
    And a keypress "s" is queued at tick 1
    And a quit keypress is queued at tick 2
    When the clock loop is executed with seconds enabled
    Then the clock ran for 2 seconds

  Scenario: Interactive key toggle for 12/24 hour format
    Given a mock clock starting at timestamp 1788523530
    And a keypress "t" is queued at tick 1
    And a quit keypress is queued at tick 2
    When the clock loop is executed in 24-hour mode
    Then the clock ran for 2 seconds

  Scenario: Interactive pause and resume
    Given a mock clock starting at timestamp 1788523530
    And a keypress " " is queued at tick 1
    And a keypress " " is queued at tick 2
    And a quit keypress is queued at tick 3
    When the clock loop is executed
    Then the clock ran for 3 seconds
