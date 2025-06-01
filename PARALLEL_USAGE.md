# Parallel Students Range Pull - Usage Examples

This new feature allows you to run multiple instances of the students range pull command concurrently, significantly speeding up the process of pulling large numbers of student records.

## New Commands

### 1. `students-range-parallel`

Run multiple parallel processes to pull student records:

```bash
# Basic usage with default settings (500 students per chunk, 10 workers)
python -m registry_cli pull students-range-parallel

# Custom chunk size and worker count
python -m registry_cli pull students-range-parallel --chunk-size 1000 --max-workers 5

# Specify custom range
python -m registry_cli pull students-range-parallel --start 901010000 --end 901000001 --chunk-size 500 --max-workers 8

# Info only mode (no programs/modules)
python -m registry_cli pull students-range-parallel --info --chunk-size 1000

# Reset progress and start fresh
python -m registry_cli pull students-range-parallel --reset
```

### 2. `students-parallel-progress`

Monitor the progress of parallel pulls:

```bash
python -m registry_cli pull students-parallel-progress
```

### 3. `students-parallel-cleanup`

Clean up progress files after completion:

```bash
python -m registry_cli pull students-parallel-cleanup
```

## How It Works

1. **Range Splitting**: The total range is split into chunks of the specified size (default 500)
2. **Parallel Processing**: Multiple worker processes run concurrently, each handling a different chunk
3. **Progress Tracking**: Each chunk has its own progress file to track failed pulls and current position
4. **Live Monitoring**: Real-time display of progress across all chunks
5. **Fault Tolerance**: If a process fails, others continue; failed students are tracked for retry

## Example Scenario

To pull 20,000 students (901020000 -> 901000001) using 10 parallel workers with 500 students per chunk:

```bash
python -m registry_cli pull students-range-parallel --start 901020000 --end 901000001 --chunk-size 500 --max-workers 10
```

This will:

- Create 40 chunks (20,000 ÷ 500)
- Run 10 workers in parallel
- Process 4 batches of 10 chunks each
- Monitor progress in real-time
- Complete much faster than sequential processing

## Progress Files

Each chunk creates a progress file named `students_range_chunk_X_progress.json` where X is the chunk ID. These files track:

- Current position in the chunk
- Failed student numbers
- Completion status
- Start/end numbers for the chunk

## Performance Benefits

- **Speed**: 5-10x faster than sequential processing (depending on hardware and network)
- **Reliability**: Individual chunk failures don't affect other chunks
- **Resumability**: Can resume from where each chunk left off
- **Monitoring**: Real-time progress tracking across all chunks

## Best Practices

1. **Chunk Size**:

   - Smaller chunks (100-500): Better fault tolerance, more frequent progress updates
   - Larger chunks (1000+): Less overhead, potentially faster overall

2. **Worker Count**:

   - Start with your CPU core count
   - Monitor system resources and adjust as needed
   - Database connection limits may constrain the maximum

3. **Environment**:

   - Use local database for development/testing
   - Use production database for actual data pulls
   - Consider network bandwidth and database load

4. **Cleanup**:
   - Run cleanup command after successful completion
   - Keep progress files if you might need to retry failed students
