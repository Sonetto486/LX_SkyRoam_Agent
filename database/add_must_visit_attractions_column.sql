-- Add must_visit_attractions column to travel_plans table

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'travel_plans'
        AND column_name = 'must_visit_attractions'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE travel_plans
        ADD COLUMN must_visit_attractions JSON DEFAULT NULL;

        RAISE NOTICE 'Added must_visit_attractions column to travel_plans table';
    ELSE
        RAISE NOTICE 'must_visit_attractions column already exists, skipping';
    END IF;
END $$;
