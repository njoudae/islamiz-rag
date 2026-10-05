<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class EnsureDatabaseSchema extends Command
{
    protected $signature = 'db:ensure-schema';

    protected $description = 'Create the PostgreSQL schema this application keeps its tables in, if it is missing';

    public function handle(): int
    {
        $connection = DB::connection();

        if ($connection->getDriverName() !== 'pgsql') {
            $this->components->info('Not a PostgreSQL connection; nothing to do.');

            return self::SUCCESS;
        }

        $schema = (string) $connection->getConfig('search_path');

        if ($schema === '' || $schema === 'public') {
            $this->components->info('Using the default "public" schema.');

            return self::SUCCESS;
        }

        if (! preg_match('/^[A-Za-z_][A-Za-z0-9_]*$/', $schema)) {
            $this->components->error("DB_SCHEMA must be a single plain identifier, got \"{$schema}\".");

            return self::FAILURE;
        }

        $connection->statement("CREATE SCHEMA IF NOT EXISTS \"{$schema}\"");

        $this->components->info("Schema \"{$schema}\" is ready.");

        return self::SUCCESS;
    }
}
