import random
from datetime import timedelta, datetime
from copy import deepcopy


def fitness(schedule_list):
    conflict_penalty = 0
    time_shift_penalty = 0

    for i in range(len(schedule_list)):
        for j in range(i + 1, len(schedule_list)):
            s1 = schedule_list[i].startTime.replace(tzinfo=None) if schedule_list[i].startTime.tzinfo else \
                schedule_list[i].startTime
            e1 = schedule_list[i].endTime.replace(tzinfo=None) if schedule_list[i].endTime.tzinfo else schedule_list[i].endTime
            s2 = schedule_list[j].startTime.replace(tzinfo=None) if schedule_list[j].startTime.tzinfo else \
                schedule_list[j].startTime
            e2 = schedule_list[j].endTime.replace(tzinfo=None) if schedule_list[j].endTime.tzinfo else schedule_list[j].endTime

            if (s1 < e2 and e1 > s2 and
                    (schedule_list[i].resource == schedule_list[j].resource or
                     schedule_list[i].executor == schedule_list[j].executor)):

                if schedule_list[i].priority > schedule_list[j].priority:
                    conflict_penalty += 10
                elif schedule_list[i].priority < schedule_list[j].priority:
                    conflict_penalty += 1
                else:
                    conflict_penalty += 5

    for schedule in schedule_list:
        if hasattr(schedule, 'original_startTime'):
            original = schedule.original_startTime.replace(
                tzinfo=None) if schedule.original_startTime.tzinfo else schedule.original_startTime
            current = schedule.startTime.replace(tzinfo=None) if schedule.startTime.tzinfo else schedule.startTime
            delta = abs((current - original).total_seconds() / 60)
            time_shift_penalty += delta / 15

    return -(conflict_penalty * 100 + time_shift_penalty)


def initialize_population(existing_schedules, new_schedule, population_size=10):
    population = []

    new_schedule.original_startTime = new_schedule.startTime

    for _ in range(population_size):
        individual = []
        adjusted_new = deepcopy(new_schedule)

        for schedule in existing_schedules:
            schedule_copy = deepcopy(schedule)
            if check_conflicts([adjusted_new], schedule_copy):
                if schedule_copy.priority < adjusted_new.priority:
                    schedule_copy.original_startTime = schedule_copy.startTime
                    base_date = schedule_copy.startTime.date()
                    random_hour = random.randint(8, 19)
                    random_minute = random.choice([0, 15, 30, 45])
                    duration = schedule_copy.endTime - schedule_copy.startTime
                    schedule_copy.startTime = datetime.combine(base_date, datetime.min.time()) + timedelta(
                        hours=random_hour, minutes=random_minute)
                    schedule_copy.endTime = schedule_copy.startTime + duration
                elif schedule_copy.priority >= adjusted_new.priority:
                    base_date = adjusted_new.startTime.date()
                    random_hour = random.randint(8, 19)
                    random_minute = random.choice([0, 15, 30, 45])
                    duration = adjusted_new.endTime - adjusted_new.startTime
                    adjusted_new.startTime = datetime.combine(base_date, datetime.min.time()) + timedelta(
                        hours=random_hour, minutes=random_minute)
                    adjusted_new.endTime = adjusted_new.startTime + duration

            individual.append(schedule_copy)

        individual.append(adjusted_new)
        population.append(individual)

    return population


def select_parents(population, fitness_scores):
    min_score = min(fitness_scores)
    adjusted_scores = [score - min_score + 1 for score in fitness_scores]
    total = sum(adjusted_scores)

    probabilities = [score / total for score in adjusted_scores]

    return random.choices(population, weights=probabilities, k=2)


def crossover(parent1, parent2):
    crossover_point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:crossover_point] + parent2[crossover_point:]
    child2 = parent2[:crossover_point] + parent1[crossover_point:]
    return child1, child2


def mutate(individual, mutation_rate=0.2):
    mutated = deepcopy(individual)

    for i in range(len(mutated)):
        schedule = mutated[i]

        if hasattr(schedule, 'original_startTime') and random.random() < mutation_rate:
            shift_minutes = random.randint(-60, 60)
            shift = timedelta(minutes=shift_minutes)

            new_start = schedule.startTime + shift
            new_end = schedule.endTime + shift

            if 8 <= new_start.hour < 22 and 8 <= new_end.hour < 22:
                schedule.startTime = new_start
                schedule.endTime = new_end

    return mutated


def genetic_algorithm(existing_schedules, new_schedule, max_generations=50):
    population = initialize_population(existing_schedules, new_schedule)

    best_individual = None
    best_fitness = float('-inf')
    no_improvement = 0

    for generation in range(max_generations):
        fitness_scores = [fitness(ind) for ind in population]

        current_best = max(fitness_scores)
        if current_best > best_fitness:
            best_fitness = current_best
            best_individual = population[fitness_scores.index(current_best)]
            no_improvement = 0
        else:
            no_improvement += 1

        if best_fitness == 0 or no_improvement >= 5:
            break

        new_population = []
        for _ in range(len(population) // 2):
            parent1, parent2 = select_parents(population, fitness_scores)
            child1, child2 = crossover(parent1, parent2)
            new_population.append(mutate(child1))
            new_population.append(mutate(child2))

        if best_individual not in new_population:
            new_population[0] = best_individual

        population = new_population

    return best_individual if best_individual else population[0]


def check_conflicts(existing_schedules, target_schedule):
    conflicts = []
    target_start = target_schedule.startTime.replace(tzinfo=None)
    target_end = target_schedule.endTime.replace(tzinfo=None)

    for schedule in existing_schedules:
        if schedule == target_schedule:
            continue

        s = schedule.startTime.replace(tzinfo=None)
        e = schedule.endTime.replace(tzinfo=None)

        if (target_start < e and target_end > s and
                (target_schedule.resource == schedule.resource or
                 target_schedule.executor == schedule.executor)):
            conflicts.append({
                "content": schedule.scheduleContent,
                "startTime": schedule.startTime,
                "endTime": schedule.endTime,
                "resource": schedule.resource,
                "executor": schedule.executor,
            })
    return conflicts
