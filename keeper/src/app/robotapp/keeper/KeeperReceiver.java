package app.robotapp.keeper;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Settings;
import android.util.Log;

/**
 * The whole app: one receiver, one line of work. On boot, turn Wireless debugging back on so the
 * laptop can reach the phone again without the cable. Nothing else, on purpose: a boot helper
 * that does one thing cannot go wrong in many ways.
 */
public final class KeeperReceiver extends BroadcastReceiver {

    private static final String TAG = "Keeper";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent != null ? String.valueOf(intent.getAction()) : "(none)";
        try {
            Settings.Global.putInt(context.getContentResolver(), "adb_wifi_enabled", 1);
            Log.i(TAG, "adb_wifi_enabled=1 after " + action);
        } catch (Exception e) {
            // WRITE_SECURE_SETTINGS missing (not granted, or the app was reinstalled) is the one
            // real failure; it lands in logcat where `robot doctor`'s next run can find it.
            Log.e(TAG, "could not set adb_wifi_enabled after " + action, e);
        }
    }
}
