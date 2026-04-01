import { createClient, SupabaseClient } from '@supabase/supabase-js';

export interface Env {
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
  SARVAM_API_KEY: string;
}

let supabase: SupabaseClient | null = null;

export const getSupabase = (env: Env) => {
  if (!supabase) {
    if (!env.SUPABASE_URL || !env.SUPABASE_ANON_KEY) {
      throw new Error('Missing Supabase credentials in environment.');
    }
    supabase = createClient(env.SUPABASE_URL, env.SUPABASE_ANON_KEY);
  }
  return supabase;
};
