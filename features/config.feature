Feature: Config loading and validation
  As a user managing timer configuration
  I want the config system to validate values strictly
  So that invalid settings are caught immediately

  Scenario: Default config loads with no file present
    Given no config file exists
    When I load the config
    Then the anim value should be None

  Scenario Outline: Valid anim modes are accepted
    Given I set anim to "<mode>"
    Then no error should be raised

    Examples:
      | mode  |
      | rich  |
      | ansi  |
      | smooth |
      | drawille |

  Scenario: Invalid anim mode raises a ValueError
    Given I set anim to "invalid_mode"
    Then a ValueError should be raised listing valid options

  Scenario: Invalid anim in config.yaml raises ValueError on load
    Given a config file containing anim "garbage"
    When I load the config
    Then a ValueError should be raised listing valid options
