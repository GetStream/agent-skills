package main

import "testing"

// TestRulesAreWellFormed guards the invariant the report depends on: every rule
// either rewrites or asks for a decision, and never both. A rule with neither
// would silently drop a call site; a rule with both would rewrite something it
// had already declared unsafe to rewrite.
func TestRulesAreWellFormed(t *testing.T) {
	for name, r := range callRules {
		switch {
		case r.review == "" && r.build == nil:
			t.Errorf("%s: has neither a review note nor a builder, so its call sites would vanish from the report", name)
		case r.review != "" && r.build != nil:
			t.Errorf("%s: has both a review note and a builder; it must do one or the other", name)
		case r.review != "" && r.behavior != "":
			t.Errorf("%s: is not rewritten, so a behavior note would never be shown", name)
		}
	}
}

// TestBehaviorNotesExplainThemselves keeps the behavior bucket useful: a note
// that does not tell the reader what to do about it is worse than none.
func TestBehaviorNotesExplainThemselves(t *testing.T) {
	for name, r := range callRules {
		if r.behavior != "" && len(r.behavior) < 40 {
			t.Errorf("%s: behavior note is too terse to act on: %q", name, r.behavior)
		}
	}
}

// TestTypeRewritesAreUnambiguous documents why the map is short. Types that
// split into request and response variants must not be listed, because picking
// one for the reader would be a guess.
func TestTypeRewritesAreUnambiguous(t *testing.T) {
	for _, ambiguous := range []string{"User", "Message", "Reaction", "Device"} {
		if to, ok := typeRewrites[ambiguous]; ok {
			t.Errorf("%s maps to %s, but it splits into request and response types; it should be reported instead", ambiguous, to)
		}
	}
}
