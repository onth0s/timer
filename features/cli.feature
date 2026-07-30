Feature: CLI commands
  As a user running the timer CLI
  I want the commands to route correctly and produce the right output
  So the tool behaves as expected from the shell

  Scenario: "timer run 5s" exits cleanly with a summary
    Given the CLI is invoked with "run 5s"
    And the clock is mocked (integer counter, no real sleep)
    And keypresses are mocked to never fire
    When the command completes
    Then the exit code should be 0
    And the output should contain summary text

  Scenario: "timer run" with no duration starts count-up mode
    Given the CLI is invoked with "run"
    And the clock is mocked
    And a quit keypress fires after 3 ticks
    When the command completes
    Then the exit code should be 0
    And the output should contain "Timer ran for"

  Scenario: "timer" bare invocation starts count-up mode
    Given the CLI is invoked with no arguments
    And the clock is mocked
    And a quit keypress fires after 2 ticks
    When the command completes
    Then the exit code should be 0
    And the output should contain "Timer ran for"

  Scenario: "timer run banana" exits with usage error
    Given the CLI is invoked with "run banana"
    When the command completes
    Then the exit code should not be 0

  Scenario: "timer config anim invalid_mode" exits with usage error
    Given the CLI is invoked with "config anim invalid_mode"
    When the command completes
    Then the exit code should not be 0

  Scenario: "timer config show" prints a config table
    Given the CLI is invoked with "config show"
    When the command completes
    Then the exit code should be 0
    And the output should contain "anim"
