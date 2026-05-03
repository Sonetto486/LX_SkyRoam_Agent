--
-- PostgreSQL database dump
--

\restrict llPFMWnPcoe7KpOQVXsTbXKRDQyFX5at4ua5kGzPd7RDuVVNjlPddvNeVBaROJN

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: attraction_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.attraction_details (
    name character varying(200) NOT NULL,
    destination character varying(100) NOT NULL,
    city character varying(100),
    phone character varying(50),
    website character varying(500),
    email character varying(100),
    wechat character varying(100),
    ticket_price double precision,
    ticket_price_child double precision,
    ticket_price_student double precision,
    currency character varying(10) NOT NULL,
    price_note text,
    opening_hours json,
    opening_hours_text text,
    address text,
    latitude double precision,
    longitude double precision,
    image_url character varying(500),
    extra_info json,
    match_priority integer NOT NULL,
    source character varying(50) NOT NULL,
    verified character varying(20) NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.attraction_details OWNER TO postgres;

--
-- Name: attraction_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.attraction_details_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attraction_details_id_seq OWNER TO postgres;

--
-- Name: attraction_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.attraction_details_id_seq OWNED BY public.attraction_details.id;


--
-- Name: destination_search; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.destination_search (
    search_id integer NOT NULL,
    user_id integer NOT NULL,
    region character varying(50),
    keyword character varying(100) NOT NULL,
    search_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.destination_search OWNER TO postgres;

--
-- Name: destination_search_search_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.destination_search_search_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.destination_search_search_id_seq OWNER TO postgres;

--
-- Name: destination_search_search_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.destination_search_search_id_seq OWNED BY public.destination_search.search_id;


--
-- Name: destinations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.destinations (
    name character varying(100) NOT NULL,
    country character varying(100) NOT NULL,
    city character varying(100),
    region character varying(100),
    latitude double precision,
    longitude double precision,
    timezone character varying(50),
    description text,
    highlights json,
    best_time_to_visit character varying(200),
    popularity_score double precision NOT NULL,
    safety_score double precision,
    cost_level character varying(20),
    images json,
    videos json,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.destinations OWNER TO postgres;

--
-- Name: destinations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.destinations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.destinations_id_seq OWNER TO postgres;

--
-- Name: destinations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.destinations_id_seq OWNED BY public.destinations.id;


--
-- Name: favorite_locations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.favorite_locations (
    user_id integer NOT NULL,
    name character varying(200) NOT NULL,
    address text,
    coordinates json,
    category character varying(50),
    phone character varying(50),
    poi_id character varying(100),
    source character varying(20),
    notes text,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.favorite_locations OWNER TO postgres;

--
-- Name: favorite_locations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.favorite_locations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.favorite_locations_id_seq OWNER TO postgres;

--
-- Name: favorite_locations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.favorite_locations_id_seq OWNED BY public.favorite_locations.id;


--
-- Name: location; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.location (
    location_id integer NOT NULL,
    location_name character varying(100) NOT NULL,
    address character varying(255),
    latitude numeric(10,7),
    longitude numeric(10,7),
    description text,
    location_type character varying(50),
    open_time character varying(100),
    phone character varying(20),
    website character varying(255),
    is_favorite boolean DEFAULT false,
    is_highlight boolean DEFAULT false,
    added_by character varying(50),
    media_images jsonb,
    facilities jsonb
);


ALTER TABLE public.location OWNER TO postgres;

--
-- Name: location_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.location_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.location_location_id_seq OWNER TO postgres;

--
-- Name: location_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.location_location_id_seq OWNED BY public.location.location_id;


--
-- Name: topic; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topic (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    intro text,
    cover_url character varying(255),
    region character varying(100),
    continent character varying(50),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.topic OWNER TO postgres;

--
-- Name: topic_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topic_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topic_id_seq OWNER TO postgres;

--
-- Name: topic_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topic_id_seq OWNED BY public.topic.id;


--
-- Name: topic_place; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topic_place (
    id bigint NOT NULL,
    topic_id bigint NOT NULL,
    related_type character varying(20) NOT NULL,
    related_id bigint NOT NULL,
    is_key_point boolean DEFAULT false NOT NULL,
    highlight_info text,
    order_index integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.topic_place OWNER TO postgres;

--
-- Name: topic_place_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topic_place_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topic_place_id_seq OWNER TO postgres;

--
-- Name: topic_place_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topic_place_id_seq OWNED BY public.topic_place.id;


--
-- Name: transport; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transport (
    transport_id integer NOT NULL,
    from_location_id integer NOT NULL,
    to_location_id integer NOT NULL,
    mode character varying(20) NOT NULL,
    distance character varying(50),
    duration character varying(50),
    is_peak_season boolean DEFAULT false,
    route_path text,
    CONSTRAINT transport_mode_check CHECK (((mode)::text = ANY ((ARRAY['步行'::character varying, '驾车'::character varying, '公共交通'::character varying])::text[])))
);


ALTER TABLE public.transport OWNER TO postgres;

--
-- Name: transport_transport_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transport_transport_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.transport_transport_id_seq OWNER TO postgres;

--
-- Name: transport_transport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transport_transport_id_seq OWNED BY public.transport.transport_id;


--
-- Name: travel_plan_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.travel_plan_items (
    title character varying(200) NOT NULL,
    description text,
    item_type character varying(50) NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    duration_hours double precision,
    location character varying(200),
    address text,
    coordinates json,
    details json,
    images json,
    travel_plan_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.travel_plan_items OWNER TO postgres;

--
-- Name: travel_plan_items_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.travel_plan_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.travel_plan_items_id_seq OWNER TO postgres;

--
-- Name: travel_plan_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.travel_plan_items_id_seq OWNED BY public.travel_plan_items.id;


--
-- Name: travel_plan_ratings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.travel_plan_ratings (
    travel_plan_id integer NOT NULL,
    user_id integer NOT NULL,
    score integer NOT NULL,
    comment text,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.travel_plan_ratings OWNER TO postgres;

--
-- Name: travel_plan_ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.travel_plan_ratings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.travel_plan_ratings_id_seq OWNER TO postgres;

--
-- Name: travel_plan_ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.travel_plan_ratings_id_seq OWNED BY public.travel_plan_ratings.id;


--
-- Name: travel_plans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.travel_plans (
    title character varying(200) NOT NULL,
    description text,
    departure character varying(100),
    destination character varying(100) NOT NULL,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone NOT NULL,
    duration_days integer NOT NULL,
    budget double precision,
    transportation character varying(50),
    preferences json,
    requirements json,
    generated_plans json,
    selected_plan json,
    status character varying(20) NOT NULL,
    score double precision,
    is_public boolean NOT NULL,
    public_at timestamp without time zone,
    user_id integer NOT NULL,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.travel_plans OWNER TO postgres;

--
-- Name: travel_plans_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.travel_plans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.travel_plans_id_seq OWNER TO postgres;

--
-- Name: travel_plans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.travel_plans_id_seq OWNED BY public.travel_plans.id;


--
-- Name: trip; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trip (
    trip_id integer NOT NULL,
    trip_name character varying(100) NOT NULL,
    days integer DEFAULT 0,
    item_count integer DEFAULT 0,
    member_count integer DEFAULT 1,
    trip_description text,
    trip_remark text,
    trip_summary text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    user_id integer NOT NULL,
    action_type character varying(50),
    action_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    start_date date,
    end_date date,
    real_time time without time zone,
    day_index integer DEFAULT 1,
    weather_forecast jsonb
);


ALTER TABLE public.trip OWNER TO postgres;

--
-- Name: trip_location; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trip_location (
    id integer NOT NULL,
    trip_id integer NOT NULL,
    location_id integer NOT NULL,
    day_index integer DEFAULT 1,
    order_index integer DEFAULT 0,
    is_stopover boolean DEFAULT false,
    is_planned boolean DEFAULT false
);


ALTER TABLE public.trip_location OWNER TO postgres;

--
-- Name: trip_location_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trip_location_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trip_location_id_seq OWNER TO postgres;

--
-- Name: trip_location_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.trip_location_id_seq OWNED BY public.trip_location.id;


--
-- Name: trip_trip_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trip_trip_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trip_trip_id_seq OWNER TO postgres;

--
-- Name: trip_trip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.trip_trip_id_seq OWNED BY public.trip.trip_id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public."user" (
    user_id integer NOT NULL,
    username character varying(50) NOT NULL,
    password character varying(255) NOT NULL,
    email character varying(100),
    favorite_locations jsonb,
    highlighted_locations jsonb,
    special_focus jsonb,
    photo_mood text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public."user" OWNER TO postgres;

--
-- Name: user_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_user_id_seq OWNER TO postgres;

--
-- Name: user_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_user_id_seq OWNED BY public."user".user_id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    full_name character varying(100),
    hashed_password character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    favorite_locations json,
    highlighted_locations json,
    special_focus json,
    photo_mood text,
    preferences text,
    travel_history text,
    is_verified boolean NOT NULL,
    last_login timestamp without time zone,
    id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: attraction_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attraction_details ALTER COLUMN id SET DEFAULT nextval('public.attraction_details_id_seq'::regclass);


--
-- Name: destination_search search_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destination_search ALTER COLUMN search_id SET DEFAULT nextval('public.destination_search_search_id_seq'::regclass);


--
-- Name: destinations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destinations ALTER COLUMN id SET DEFAULT nextval('public.destinations_id_seq'::regclass);


--
-- Name: favorite_locations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.favorite_locations ALTER COLUMN id SET DEFAULT nextval('public.favorite_locations_id_seq'::regclass);


--
-- Name: location location_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location ALTER COLUMN location_id SET DEFAULT nextval('public.location_location_id_seq'::regclass);


--
-- Name: topic id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic ALTER COLUMN id SET DEFAULT nextval('public.topic_id_seq'::regclass);


--
-- Name: topic_place id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_place ALTER COLUMN id SET DEFAULT nextval('public.topic_place_id_seq'::regclass);


--
-- Name: transport transport_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transport ALTER COLUMN transport_id SET DEFAULT nextval('public.transport_transport_id_seq'::regclass);


--
-- Name: travel_plan_items id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_items ALTER COLUMN id SET DEFAULT nextval('public.travel_plan_items_id_seq'::regclass);


--
-- Name: travel_plan_ratings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_ratings ALTER COLUMN id SET DEFAULT nextval('public.travel_plan_ratings_id_seq'::regclass);


--
-- Name: travel_plans id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plans ALTER COLUMN id SET DEFAULT nextval('public.travel_plans_id_seq'::regclass);


--
-- Name: trip trip_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip ALTER COLUMN trip_id SET DEFAULT nextval('public.trip_trip_id_seq'::regclass);


--
-- Name: trip_location id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_location ALTER COLUMN id SET DEFAULT nextval('public.trip_location_id_seq'::regclass);


--
-- Name: user user_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user" ALTER COLUMN user_id SET DEFAULT nextval('public.user_user_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: attraction_details attraction_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.attraction_details
    ADD CONSTRAINT attraction_details_pkey PRIMARY KEY (id);


--
-- Name: destination_search destination_search_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destination_search
    ADD CONSTRAINT destination_search_pkey PRIMARY KEY (search_id);


--
-- Name: destinations destinations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destinations
    ADD CONSTRAINT destinations_pkey PRIMARY KEY (id);


--
-- Name: favorite_locations favorite_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.favorite_locations
    ADD CONSTRAINT favorite_locations_pkey PRIMARY KEY (id);


--
-- Name: location location_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (location_id);


--
-- Name: topic topic_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic
    ADD CONSTRAINT topic_pkey PRIMARY KEY (id);


--
-- Name: topic_place topic_place_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_place
    ADD CONSTRAINT topic_place_pkey PRIMARY KEY (id);


--
-- Name: transport transport_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transport
    ADD CONSTRAINT transport_pkey PRIMARY KEY (transport_id);


--
-- Name: travel_plan_items travel_plan_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_items
    ADD CONSTRAINT travel_plan_items_pkey PRIMARY KEY (id);


--
-- Name: travel_plan_ratings travel_plan_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_ratings
    ADD CONSTRAINT travel_plan_ratings_pkey PRIMARY KEY (id);


--
-- Name: travel_plans travel_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plans
    ADD CONSTRAINT travel_plans_pkey PRIMARY KEY (id);


--
-- Name: trip_location trip_location_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_location
    ADD CONSTRAINT trip_location_pkey PRIMARY KEY (id);


--
-- Name: trip_location trip_location_trip_id_location_id_day_index_order_index_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_location
    ADD CONSTRAINT trip_location_trip_id_location_id_day_index_order_index_key UNIQUE (trip_id, location_id, day_index, order_index);


--
-- Name: trip trip_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip
    ADD CONSTRAINT trip_pkey PRIMARY KEY (trip_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (user_id);


--
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_location_is_favorite; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_location_is_favorite ON public.location USING btree (is_favorite);


--
-- Name: idx_location_is_highlight; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_location_is_highlight ON public.location USING btree (is_highlight);


--
-- Name: idx_location_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_location_name ON public.location USING btree (location_name);


--
-- Name: idx_search_keyword; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_search_keyword ON public.destination_search USING btree (keyword);


--
-- Name: idx_search_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_search_time ON public.destination_search USING btree (search_time);


--
-- Name: idx_search_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_search_user_id ON public.destination_search USING btree (user_id);


--
-- Name: idx_topic_continent; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_continent ON public.topic USING btree (continent);


--
-- Name: idx_topic_place_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_place_order ON public.topic_place USING btree (topic_id, order_index);


--
-- Name: idx_topic_place_topic_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_place_topic_id ON public.topic_place USING btree (topic_id);


--
-- Name: idx_topic_region; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_region ON public.topic USING btree (region);


--
-- Name: idx_transport_from; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_transport_from ON public.transport USING btree (from_location_id);


--
-- Name: idx_transport_to; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_transport_to ON public.transport USING btree (to_location_id);


--
-- Name: idx_trip_action_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trip_action_time ON public.trip USING btree (action_time);


--
-- Name: idx_trip_location_location_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trip_location_location_id ON public.trip_location USING btree (location_id);


--
-- Name: idx_trip_location_trip_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trip_location_trip_id ON public.trip_location USING btree (trip_id);


--
-- Name: idx_trip_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_trip_user_id ON public.trip USING btree (user_id);


--
-- Name: idx_user_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_username ON public."user" USING btree (username);


--
-- Name: ix_attraction_details_city; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attraction_details_city ON public.attraction_details USING btree (city);


--
-- Name: ix_attraction_details_destination; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attraction_details_destination ON public.attraction_details USING btree (destination);


--
-- Name: ix_attraction_details_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attraction_details_id ON public.attraction_details USING btree (id);


--
-- Name: ix_attraction_details_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_attraction_details_name ON public.attraction_details USING btree (name);


--
-- Name: ix_destinations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_destinations_id ON public.destinations USING btree (id);


--
-- Name: ix_destinations_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_destinations_name ON public.destinations USING btree (name);


--
-- Name: ix_favorite_locations_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_favorite_locations_id ON public.favorite_locations USING btree (id);


--
-- Name: ix_travel_plan_items_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_travel_plan_items_id ON public.travel_plan_items USING btree (id);


--
-- Name: ix_travel_plan_ratings_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_travel_plan_ratings_id ON public.travel_plan_ratings USING btree (id);


--
-- Name: ix_travel_plans_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_travel_plans_id ON public.travel_plans USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: destination_search destination_search_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destination_search
    ADD CONSTRAINT destination_search_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(user_id) ON DELETE CASCADE;


--
-- Name: favorite_locations favorite_locations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.favorite_locations
    ADD CONSTRAINT favorite_locations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: topic_place topic_place_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_place
    ADD CONSTRAINT topic_place_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topic(id) ON DELETE CASCADE;


--
-- Name: transport transport_from_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transport
    ADD CONSTRAINT transport_from_location_id_fkey FOREIGN KEY (from_location_id) REFERENCES public.location(location_id) ON DELETE CASCADE;


--
-- Name: transport transport_to_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transport
    ADD CONSTRAINT transport_to_location_id_fkey FOREIGN KEY (to_location_id) REFERENCES public.location(location_id) ON DELETE CASCADE;


--
-- Name: travel_plan_items travel_plan_items_travel_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_items
    ADD CONSTRAINT travel_plan_items_travel_plan_id_fkey FOREIGN KEY (travel_plan_id) REFERENCES public.travel_plans(id);


--
-- Name: travel_plan_ratings travel_plan_ratings_travel_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_ratings
    ADD CONSTRAINT travel_plan_ratings_travel_plan_id_fkey FOREIGN KEY (travel_plan_id) REFERENCES public.travel_plans(id);


--
-- Name: travel_plan_ratings travel_plan_ratings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plan_ratings
    ADD CONSTRAINT travel_plan_ratings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: travel_plans travel_plans_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.travel_plans
    ADD CONSTRAINT travel_plans_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: trip_location trip_location_location_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_location
    ADD CONSTRAINT trip_location_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.location(location_id) ON DELETE CASCADE;


--
-- Name: trip_location trip_location_trip_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip_location
    ADD CONSTRAINT trip_location_trip_id_fkey FOREIGN KEY (trip_id) REFERENCES public.trip(trip_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict llPFMWnPcoe7KpOQVXsTbXKRDQyFX5at4ua5kGzPd7RDuVVNjlPddvNeVBaROJN

