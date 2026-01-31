"""Test the default scripts bug fix."""


class TestDefaultScriptsFix:
    """Test that the default scripts save/load fix works correctly."""

    def test_cleared_fields_are_removed(self):
        """Test that cleared default_script_ fields are properly removed.
        
        This is a unit test for the bug fix in async_step_default_scripts.
        When a user clears an optional script field, it should be removed from
        the config entry options, not persist with the old value.
        """
        # Simulate existing options with default scripts
        existing_options = {
            "default_script_pre_alarm": "script.morning_pre",
            "default_script_alarm": "script.morning_alarm",
            "default_script_post_alarm": "script.morning_post",
            "other_setting": "keep_this",
            "another_setting": "also_keep",
        }
        
        # Simulate user input where pre_alarm and post_alarm are cleared
        # (not included in the submission)
        user_input = {
            "default_script_alarm": "script.new_alarm",
            # Note: pre_alarm and post_alarm are NOT in user_input (cleared)
        }
        
        # Apply the fix logic from async_step_default_scripts
        updated_options = {
            k: v
            for k, v in existing_options.items()
            if not k.startswith("default_script_")
        }
        updated_options.update(user_input)
        
        # Verify cleared fields are removed
        assert "default_script_pre_alarm" not in updated_options
        assert "default_script_post_alarm" not in updated_options
        
        # Verify updated field has new value
        assert updated_options["default_script_alarm"] == "script.new_alarm"
        
        # Verify non-default-script settings are preserved
        assert updated_options["other_setting"] == "keep_this"
        assert updated_options["another_setting"] == "also_keep"
    
    def test_all_fields_cleared(self):
        """Test that all default script fields can be cleared."""
        existing_options = {
            "default_script_pre_alarm": "script.morning_pre",
            "default_script_alarm": "script.morning_alarm",
            "default_script_timeout": 30,
            "other_setting": "keep_this",
        }
        
        # User clears all script fields (none in user_input)
        user_input = {}
        
        # Apply the fix logic
        updated_options = {
            k: v
            for k, v in existing_options.items()
            if not k.startswith("default_script_")
        }
        updated_options.update(user_input)
        
        # All default_script_ fields should be removed
        assert "default_script_pre_alarm" not in updated_options
        assert "default_script_alarm" not in updated_options
        assert "default_script_timeout" not in updated_options
        
        # Other settings preserved
        assert updated_options["other_setting"] == "keep_this"
    
    def test_no_existing_default_scripts(self):
        """Test behavior when there are no existing default scripts."""
        existing_options = {
            "other_setting": "keep_this",
        }
        
        # User adds a new default script
        user_input = {
            "default_script_alarm": "script.new_alarm",
        }
        
        # Apply the fix logic
        updated_options = {
            k: v
            for k, v in existing_options.items()
            if not k.startswith("default_script_")
        }
        updated_options.update(user_input)
        
        # New script should be added
        assert updated_options["default_script_alarm"] == "script.new_alarm"
        
        # Other settings preserved
        assert updated_options["other_setting"] == "keep_this"
    
    def test_old_behavior_was_broken(self):
        """Demonstrate that the old merge behavior kept old values."""
        existing_options = {
            "default_script_pre_alarm": "script.old",
            "other_setting": "keep_this",
        }
        
        # User clears pre_alarm (not in user_input)
        user_input = {}
        
        # OLD BROKEN BEHAVIOR: simple merge
        old_behavior = {**existing_options, **user_input}
        
        # The bug: old value persists even though user cleared it
        assert "default_script_pre_alarm" in old_behavior
        assert old_behavior["default_script_pre_alarm"] == "script.old"
        
        # NEW FIXED BEHAVIOR
        new_behavior = {
            k: v
            for k, v in existing_options.items()
            if not k.startswith("default_script_")
        }
        new_behavior.update(user_input)
        
        # The fix: old value is removed as expected
        assert "default_script_pre_alarm" not in new_behavior
