<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;

class AdminUserSeeder extends Seeder
{
    /**
     * Create the single administrator, or bring it back in line with the
     * configured credentials. Safe to run on every deploy.
     */
    public function run(): void
    {
        // Reuse the existing administrator, so changing ADMIN_EMAIL renames the account
        // instead of leaving the old address able to log in.
        $admin = User::where('email', config('daleel.admin.email'))->first()
            ?? User::where('is_admin', true)->oldest('id')->first()
            ?? new User;

        $admin->email = config('daleel.admin.email');

        $admin->name = config('daleel.admin.name');
        $admin->password = config('daleel.admin.password');
        $admin->is_admin = true;
        $admin->email_verified_at ??= now();
        $admin->save();
    }
}
