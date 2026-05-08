namespace Loupedeck.DemoPlugin
{
    using System;
    using System.Collections.Generic;
    using System.Linq;

    /// <summary>
    /// Manages the current voice target (single ally or ALL),
    /// and stores role/hero configuration received from the PC UI.
    /// </summary>
    internal static class AllyChannelState
    {
        public const Int32 AllySlotCount = 4;  // 5v5: 4 allies
        public const Int32 EnemySlotCount = 5;  // 5 enemies

        private static readonly Object LockObject = new Object();

        // Slot index (0-3) → role name ("JG", "MID", …). Empty string = unassigned.
        private static readonly String[] AllyRoles = new String[AllySlotCount];

        // Current voice target: null/"" = broadcast ALL, otherwise a role name.
        private static String _currentTarget = "";

        // Enemy slots (0-4) → hero name.
        private static readonly String[] EnemyHeroes = new String[EnemySlotCount];

        // My own role + hero.
        private static String _myRole = "";
        private static String _myHero = "";

        static AllyChannelState()
        {
            for (var i = 0; i < AllySlotCount; i++)
                AllyRoles[i] = "";
            for (var i = 0; i < EnemySlotCount; i++)
                EnemyHeroes[i] = "";
        }

        /// <summary>Fired when target or config changes. Param = changed slot (1-based), or 0 for global.</summary>
        public static event Action<Int32> StateChanged;

        // ── My info ────────────────────────────────────────────────

        public static void SetMyRole(String role)
        {
            lock (LockObject) { _myRole = role ?? ""; }
            RaiseStateChanged(0);
        }

        public static String GetMyRole()
        {
            lock (LockObject) { return _myRole; }
        }

        public static void SetMyHero(String hero)
        {
            lock (LockObject) { _myHero = hero ?? ""; }
        }

        public static String GetMyHero()
        {
            lock (LockObject) { return _myHero; }
        }

        // ── Ally config ────────────────────────────────────────────

        public static void SetAllyRole(Int32 slot, String role)
        {
            var idx = ValidateSlot(slot, AllySlotCount);
            lock (LockObject) { AllyRoles[idx] = role ?? ""; }
            RaiseStateChanged(slot);
        }

        public static String GetAllyRole(Int32 slot)
        {
            var idx = ValidateSlot(slot, AllySlotCount);
            lock (LockObject) { return AllyRoles[idx]; }
        }

        // ── Enemy config ───────────────────────────────────────────

        public static void SetEnemyHero(Int32 slot, String heroName)
        {
            var idx = ValidateSlot(slot, EnemySlotCount);
            lock (LockObject) { EnemyHeroes[idx] = heroName ?? ""; }
        }

        public static String GetEnemyHero(Int32 slot)
        {
            var idx = ValidateSlot(slot, EnemySlotCount);
            lock (LockObject) { return EnemyHeroes[idx]; }
        }

        // ── Voice Target (single target, not a set) ────────────────

        /// <summary>
        /// Toggle target for a specific ally slot.
        /// If currently targeting this ally → revert to ALL.
        /// If currently targeting another ally or ALL → switch to this ally.
        /// </summary>
        public static void ToggleTarget(Int32 slot)
        {
            var idx = ValidateSlot(slot, AllySlotCount);
            lock (LockObject)
            {
                var role = AllyRoles[idx];
                if (String.IsNullOrEmpty(role))
                    return;

                if (_currentTarget == role)
                    _currentTarget = "";  // back to broadcast
                else
                    _currentTarget = role;  // switch to this ally
            }
            RaiseStateChanged(0); // refresh all buttons
        }

        /// <summary>Force broadcast mode (ALL).</summary>
        public static void ClearTarget()
        {
            lock (LockObject) { _currentTarget = ""; }
            RaiseStateChanged(0);
        }

        /// <summary>Current target role, or empty string for broadcast ALL.</summary>
        public static String GetCurrentTarget()
        {
            lock (LockObject) { return _currentTarget; }
        }

        /// <summary>True if the specified slot is the current voice target.</summary>
        public static Boolean IsTargeted(Int32 slot)
        {
            var idx = ValidateSlot(slot, AllySlotCount);
            lock (LockObject)
            {
                return !String.IsNullOrEmpty(_currentTarget)
                    && _currentTarget == AllyRoles[idx];
            }
        }

        // ── Helpers ────────────────────────────────────────────────

        private static Int32 ValidateSlot(Int32 slot, Int32 max)
        {
            if (slot < 1 || slot > max)
                throw new ArgumentOutOfRangeException(nameof(slot), $"Slot must be 1-{max}");
            return slot - 1;
        }

        private static void RaiseStateChanged(Int32 slot)
            => StateChanged?.Invoke(slot);
    }
}
