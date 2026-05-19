-- Add favorite_travel_plans table
CREATE TABLE IF NOT EXISTS favorite_travel_plans (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  travel_plan_id INTEGER NOT NULL REFERENCES travel_plans(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE (user_id, travel_plan_id)
);
