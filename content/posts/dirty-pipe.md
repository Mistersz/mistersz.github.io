---
title: "cleaning the dirtiest of the pipes"
date: 2026-10-06
draft: true
summary: "trying to clean up those dirty pipes (study on CVE-2022-0847)"
description: "deep dive on Dirty Pipe (CVE-2022-0847) and its inner workings"
tags: ["research", "analysis"]
categories: ["analysis"]
ShowToc: true
TocOpen: false
weight: 1
# cover:
#   image: "images/babyqemu-cover.png"   # optional: drop a cover in assets or static/
#   alt: "babyqemu"
#   caption: ""
#   relative: false
---


## Introduction

Imagine a world where reading data from files leads you to corrupted bytes,
which eventually would reveal themselves to be the result of an extremely interesting chain 
of coincidencies that brought up to light the unintended interacting behaviour between
the Linux Pipe Subsystem and Memmory Management Subsystem (leading to a priv escal).

That is what happened with Max Kellerman, when he disclosed his findings on the 
Dirty Pipe (CVE-2022-0847) vulnerability, which allowed basically arbitrary write
on the page cache. This primitive, on that specific memory region, allows for privilege
escalation, corruption of `/etc/passwd` file, manufacturing ssh keys, sudo hijacking and more.
Accounting it's impact and low execution complexity, Dirty Pipe was crowned with
a CVSSv3 score of 7.8 (high) by NVD.

So let's tag along and understand how this was even possible. This post will try to explain
the inner workings of each component that lead the vulnerability to work and their relations,
by the following structure:

    1. Understanding what the vulnerability is
    2. Which OS components are involved into
    3. How these components work under the hood
    4. How they tie together
    5. The exploit

For me, this vulnerability is amazing since the moment of its discovery
to it's exploration, not only due it's simplicity but also by the way
it was discovered and researched. In the end, i took the liberty to 
write some thoughts about the process of the discovery of the vuln.


----------------------

# What happened? (what it actually is)

Imagine you have those two C programs:

```c
#include <unistd.h>
int main(int argc, char **argv) {
  for (;;) write(1, "AAAAA", 5);
}
// ./writer >foo
```

<small>Source: <a href="https://dirtypipe.cm4all.com/">Max Kellermann — minimal reproducer, writer program</a></small>

```c

#define _GNU_SOURCE
#include <unistd.h>
#include <fcntl.h>
int main(int argc, char **argv) {
  for (;;) {
    splice(0, 0, 1, 0, 2, 0);
    write(1, "BBBBB", 5);
  }
}
// ./splicer <foo |cat >/dev/null

```

<small>Source: <a href="https://dirtypipe.cm4all.com/">Max Kellermann — minimal reproducer, splicer program</a></small>


Basically, what is happening here is:

-> The first program writes, indefinitely, 5 bytes of data ("AAAAA") to the "foo" file, which is
where the program's file descriptor 1 (stdout) points to in this case. 

-> The second program copies the data received from stdin (in this case, the data from foo file)
to it's stdout, in this case a pipe. This happens through the `splice()` syscall. And then it also 
writes 5 bytes of data ("BBBBB") to it's stdout (the pipe).


Given those, one would expect the data from the file to just be redirected by the pipe to another
programs stdin (in our case, that would be cat >/dev/null). But in reality, after some time,
what happens is:

    "Some BBBBB's started appearing at the foo's file"


This should be considered impossible, since in any moment the write happens inside the file.
BBBBB is being written into the program's stdout i.e the pipe. But, in reality, seems like
the pipe writes to the foo file, even tho it doesn't have permissions to do so.


# Components involved

So, first of all, let's see which components and implementations are involved into this
strange behaviour.

Separating the experiment onto it's functionalities we have:

    i. A file with data, stored in the hard-drive
    ii. A program which reads the file's content and redirects to a pipe via `splice()`
    iii. Writes to a pipe previously used 

The following questions (processes?) become key for understandment

    i. How file data gets transfered to memory for use?
    ii. What are pipes and how they get data onto it?
    iii. `splice()` behaviour with ( file -> pipe ) data transfer
    iv. How pipes process writes and subsequent writes?

----------------

## Theory and inner workings


### 1. Memory

The operating system handles memory via operations on it's smallest representation unit:
a page.

Pages are merely the name that is given for a continous region of 4KiB (4 * 2^10 bytes)
of memory address. Basically, each page carries over 4096 bytes, so 4096 addresses.
In hexadecimal notation that would be `0x1000` bytes.

Page size varies accordantly the CPU architecture (MMU) and OS directives, certain architectures
allow for bigger and smaller page size. We are considering here the classical x86/x86-64 (same as
RISC-V btw).

When a program reads data from a file for the first time, the kernel copies a number of page chunks from the hard-drive
to kernel memory (RAM). The subsystem responsible for storaging and managing those types of pages (file-backed pages)
is called the page cache. 

From the page cache (kernel memory), the contents inside the loaded pages can then be transfered to userspace or
be directly mmap()ed into a process's address space.

This seems intuitive (and it is, i mean, thats why RAM exists for i.e storing data for CPU to use) but
there is an interesting cavenant here: 

Not all the syscalls "behave" the same. The way system calls are implemented define how they interact with memory, files, other subsystems, processes and more.
For example, the `read()` syscall takes a copy from a file's data and writes it into an specified buffer.
Meanwhile, as Max pointed out on his disclousure, `splice()` and `sendfile()` are considered zero-copy,
meaning that those syscalls do not make copies of whatever bytes they are transfering, instead
they do it by reference (with pointers!).


### 2. Pipes

A pipe (|) is a mechanism used by the Linux Kernel (and also a lot of other operating systems / kernels) for 
transfering data to one end to another in a unidirectional way. Those "ends" being file descriptors.

So, if we have, supposing `/tmp/dummy`:

```bash
./program1 | cat > /tmp/dummy
```

Whatever is coming out from ./program1's stdout (file descriptor 1) is getting transfered to
cat's stdin (file descriptor 0)

This is the basic behaviour of pipes, so now let's take a look on how pipes are implemented on actual
C code.

On Kernel Linux, pipes are implemented as a ring buffer. 

![Ring buffer's visualization](/images/dirty-pipe/ringbuffer.png)

Ring buffers are essentially a circular array buffer. They hold two important integers, `head` and `tail`, which are the indexes of the next slot to write
and next slot to read, respectively. For accessing elements on the array, a bitwise AND is performed with a variable called `mask`
which is ring buffer size - 1. Basically emulating a modulo operation.

The `pipe_inode_info` struct describe it's implementation on pipes. As you notice, pipes are represented by
this ring buffer of `pipe_buffer` structs.
```c

struct pipe_inode_info {
    unsigned int head;
    unsigned int tail;
    unsigned int ring_size;
    struct pipe_buffer *bufs;
    ............
};

```

<small>Source: <a href="https://blogs.oracle.com/linux/pipe-and-splice">Linux 5.19 — pipe_inode_info (abridged); see Oracle Linux</a></small>

`ring_size` is normally 16 on Linux Kernel, meaning 16 `pipe_buffer` entries.

The `pipe_buffer` struct is defined as follows:

```c

struct pipe_buffer {
    struct page *page;
    unsigned int offset, len;
    const struct pipe_buf_operations *ops;
    unsigned int flags;
    unsigned long private;
};

```

<small>Source: <a href="https://github.com/torvalds/linux/blob/v5.19/include/linux/pipe_fs_i.h">Linux 5.19 — struct pipe_buffer</a></small>

The page pointer holds the address containing the page with pipe buffer data.
`offset` and `len` define the buffer's range within the page. `offset` is the lower bound
for reads on the page, while `len`, is the number of bytes written and not consumed by a read
on the buffer. When a read is perfomed, the `offset` field is increased by the same amount `len`
is decreased, preserving the bytes that still need to be read out the buffer.

One important thing to estabilish is: what is an anonymous pipe?
They are pipes that are not backed by a file on the file system, which by consequence,
makes them ethereal (they only exists as long as the processes on each end exist).

pipe buffers (the `pipe_buffer` struct) are called anonymous when the page they reference
is not a page cache entry. When they do not completely fill the page they are writing to, 
subsequential writes may append the content to what was already written, instead of allocating 
a new page.

This behaviour is attributed to a pipe via the `PIPE_BUF_FLAG_CAN_MERGE` flag (which is a just a directive
for `0x10`), since the checking for the flag is a bitwise operation.

```c

#define PIPE_BUF_FLAG_CAN_MERGE 0x10 /* can merge buffers */

```

<small>Source: <a href="https://github.com/torvalds/linux/blob/v5.19/include/linux/pipe_fs_i.h">Linux 5.19 — PIPE_BUF_FLAG_CAN_MERGE definition</a></small>




### 3. `splice()` workings

`splice()` is a linux system call that allows transfering data between two file descriptors where one of them
must be a pipe. As discussed before, transfering data this way, does not make a trip to userland.

Let's focus on the specific case transfering data from a file to a pipe.

For transfering data from the file to the pipe, `splice()` invokes a set of functions that are
going to be responsible for setting the page cache sharing operation.

Since page cache data may be non-continous, `splice()` uses the machinery of the `iov_iter` interface
to supply arguments and parameters (among them, iterators) to memory management functions that are called by it.

Taking a look at the stack trace for `splice()`:


![Splice's stack trace](/images/dirty-pipe/splice.png)

Focusing on the last functions that are called:

    - `copy_page_to_iter()`
    - `__copy_page_to_iter()`
    - `copy_page_to_iter_pipe()`

`copy_page_to_iter()` is responsible for transfering the data from the page cache pages
in the folio (base page of consecutive pages) to the iov iterator (reference by iter), used by the 
pipe for reading the file data.

It calls `__copy_page_to_iter()` in a loop, handling iov iterator and calls 
appropriartly. By the end, `copy_page_to_iter_pipe()` is called, since is the function that 
handles transfers between file backed data to a pipe. It assigns `buf->page` to the 
page cache's page address, alongside with `len`, `offset` and `ops`. 

`copy_page_to_iter_pipe()` body:

```c

static size_t copy_page_to_iter_pipe(struct page *page, size_t offset, size_t bytes,
			 struct iov_iter *i)
{
	struct pipe_inode_info *pipe = i->pipe;
	struct pipe_buffer *buf;
	size_t off;
	int idx;

	if (unlikely(bytes > i->count))
		bytes = i->count;

	if (unlikely(!bytes))
		return 0;

	if (!sanity(i))
		return 0;

	off = i->iov_offset;
	idx = i->idx;
	buf = &pipe->bufs[idx];
	if (off) {
		if (offset == off && buf->page == page) {
			/* merge with the last one */
			buf->len += bytes;
			i->iov_offset += bytes;
			goto out;
		}
		idx = next_idx(idx, pipe);
		buf = &pipe->bufs[idx];
	}
	if (idx == pipe->curbuf && pipe->nrbufs)
		return 0;
	pipe->nrbufs++;
	buf->ops = &page_cache_pipe_buf_ops;
	get_page(buf->page = page);
	buf->offset = offset;
	buf->len = bytes;
	i->iov_offset = offset + bytes;
	i->idx = idx;
out:
	i->count -= bytes;
	return bytes;
}
```

<small>Source: <a href="https://github.com/torvalds/linux/commit/241699cd72a8489c9446ae3910ddd243e9b9061b">Linux commit 241699cd72a8 — copy_page_to_iter_pipe() (historical implementation)</a></small>

Seems reasonable and normal, right? 

### 4. Writes to pipes

Writes to pipes are handled by the `pipe_write()` function. Newer kernel linux versions
split it into two functions: `anon_pipe_write()` and `fifo_pipe_write()`.

Firstly, it selects the current `pipe_buffer` struct that is pointed by the `head` of the pipe, to
check if the pipe is full.

If not, it advances the `head` and inserts the allocated page into the buffer array (pointed by the `head`),
as well as setting up its other fields: `ops`, `offset`, `len` and `flags`.

```c

for (;;) {
    head = pipe->head;
    if (!pipe_full(head, pipe->tail, pipe->max_usage)) {
        unsigned int mask = pipe->ring_size - 1;
        struct pipe_buffer *buf = &pipe->bufs[head & mask];
        struct page *page = NULL;
        int copied;

        if (!page) {
            page = alloc_page(GFP_HIGHUSER | __GFP_ACCOUNT);
            if (unlikely(!page)) {
                ret = ret ? : -ENOMEM;
                break;
            }
        }

        /* Allocate a slot in the ring in advance and attach an
         * empty buffer.  If we fault or otherwise fail to use
         * it, either the reader will consume it or it'll still
         * be there for the next write.
         */
        spin_lock_irq(&pipe->rd_wait.lock);

        head = pipe->head;
        if (pipe_full(head, pipe->tail, pipe->max_usage)) {
            spin_unlock_irq(&pipe->rd_wait.lock);
            continue;
        }

        pipe->head = head + 1;
        spin_unlock_irq(&pipe->rd_wait.lock);


```

And then, the user buffer is copied to the allocated page.



```c

/* Insert it into the buffer array */
        buf = &pipe->bufs[head & mask];
        buf->page = page;
        buf->ops = &anon_pipe_buf_ops;
        buf->offset = 0;
        buf->len = 0;
        if (is_packetized(filp))
            buf->flags = PIPE_BUF_FLAG_PACKET;
        else
            buf->flags = PIPE_BUF_FLAG_CAN_MERGE;

        copied = copy_page_from_iter(page, 0, PAGE_SIZE, from);
        if (unlikely(copied < PAGE_SIZE && iov_iter_count(from))) {
            if (!ret)
                ret = -EFAULT;
            break;
        }

        ret += copied;
        buf->offset = 0;
        buf->len = copied;

        if (!iov_iter_count(from))
            break;
    }

```

<small>Source: <a href="https://blogs.oracle.com/linux/pipe-and-splice">Oracle Linux — pipe_write() excerpt, Linux 5.19</a></small>

On this code snippet, you can check another function that also belongs to the iov interface. 
`copy_page_from_iter()`, resposible from copying contents (in this case, the user buffer) present
on the iterator to the refered page. 

The bytes written to it are stored on the page it points to, for anonymous pipes, this would
be a page similar to an anonymous one.

Remember, all read and write operations on the page are within the range of `buf->offset` and `buf->offset + buf->len`.

Subsequential writes to the pipe normally follow the behaviour described above, 
advancing the `head` and setting up fields for the ring slot. [ check ]

But if the `PIPE_BUF_FLAG_CAN_MERGE` is set and a write happens the new inserted content 
is going to be appended to the page pointed by the `pipe_buffer` struct, instead of allocating 
a new `pipe_buffer` and moving the ring's `head`.

```c

buf = &pipe->bufs[(head - 1) & mask];
int offset = buf->offset + buf->len;

if ((buf->flags & PIPE_BUF_FLAG_CAN_MERGE) &&
    offset + chars <= PAGE_SIZE) {
    ...
    ret = copy_page_from_iter(buf->page, offset, chars, from);
    buf->len += ret;
}

```



# How they tie together

Now, with more information about how things are handled on a lower abstraction level,
Lets remember the functionalities that we talked about earlier and relate it to our
new knowledge.

    i. A file with data, stored in the hard-drive
       |
       |
       |
       |-> file data is loaded on the page cache for use, in our case, we will
           be given a direct reference to its address so we can interact with it.

    ii. A program which reads the file's content and redirects to a pipe via `splice()`
        |
        |
        |
        |-> splice() ultimatelly invokes copy_page_to_iter_pipe() to initialize a 
            pipe_buffer for storing the contents of the file.

    iii. Writes to a pipe previously used 
         |
         |
         |
         |-> Writes on pipes happen on the page pointed by pipe_buffer. The behaviour
             of subsequential writes vary depending on the initialized flags on 
             pipe_buffer. Is possible for content to be appended if the 
             PIPE_BUF_FLAG_CAN_MERGE is setted.


In theory, following what we discussed, everything should be alright and it should not result
in unintended behaviour. Everything seems to work, but in one of the assumptions above there is 
a subtle detail that is the reason why im writing this blogpost.

All said in the above is true and unfortunelly this is also the problem. (or fortunelly, i like this vuln)
The atentive reader might have been able to notice, but:

       splice() ultimatelly invokes copy_page_to_iter_pipe() to initialize a 
                 pipe_buffer for storing the contents of the file.

Checking on all assignments made to the buf variable on `copy_page_to_iter_pipe()`:

```c
	buf = &pipe->bufs[idx];
	if (off) {
		if (offset == off && buf->page == page) {
			/* merge with the last one */
			buf->len += bytes;
			i->iov_offset += bytes;
			goto out;
		}
		idx = next_idx(idx, pipe);
		buf = &pipe->bufs[idx];
	}
	if (idx == pipe->curbuf && pipe->nrbufs)
		return 0;
	pipe->nrbufs++;
	buf->ops = &page_cache_pipe_buf_ops;
	get_page(buf->page = page);
	buf->offset = offset;
	buf->len = bytes;
	i->iov_offset = offset + bytes;
	i->idx = idx;
out:
	i->count -= bytes;
	return bytes;
}
```

<small>Source: <a href="https://github.com/torvalds/linux/commit/241699cd72a8489c9446ae3910ddd243e9b9061b">Linux commit 241699cd72a8 — copy_page_to_iter_pipe() excerpt</a></small>

There are no mentions to `buf->flag` at all, which means that `copy_page_to_iter_pipe()`
fails at setting `flags` for the `pipe_buffer`. Wait, what does this mean for the pipe?

If that instance of `pipe_buffer` was not previously used, it would have no `flags` initialized
but if it was indeed used, specially by an anonymous pipe, the flag would still be setted, since
no new value was assigned to `buf->flag`, overwriting what was previously there.

With this new info we now have:    

    i. A file with data, stored in the hard-drive
       |
       |
       |
       |-> file data is loaded on the page cache for use, in our case, we will
           be given a direct reference to its address so we can interact with it.
                |
                |------> Page cache reference.

    ii. A program which reads the file's content and redirects to a pipe via `splice()`
        |
        |
        |
        |-> splice() ultimatelly invokes copy_page_to_iter_pipe() to initialize a 
            pipe_buffer for storing the contents of the file.
                |
                |-----> Persistance of flag allowing subsequential writes to a page
                        on a pipe_buffer.


    iii. Writes to a pipe previously used  
         |
         |
         |
         |-> Writes on pipes happen on the page pointed by pipe_buffer. The behaviour
             of subsequential writes vary depending on the initialized flags on 
             pipe_buffer. Is possible for content to be appended if the 
             PIPE_BUF_FLAG_CAN_MERGE is setted.
                |
                |-----> Writes directly happen on the page pointed by pipe_buffer.



Combining it all together we now have an extremelly powerful primitive:

    A limited arbitrary write to the page cache.

This would explain why BBBBB's started appearing on the file! Even though the write is made
to a pipe, that pipe holded (somewhere) a reference to the page cache!

The last piece is how to modularized this into a systematic approach in order to exploit it.


# The exploit (finally)

Basically we have to manufacture the conditions that we observed from the experiment and
achieve by the end:

    A pipe with pipe buffers holding a page cache reference, with `PIPE_BUF_FLAG_CAN_MERGE` setted.

With our given machinery, we do have some limitations:

    1. Need for read permission on the file, since `splice()` needs it.
    2. We can't neither start at / cross a page boundaries from the page cache.
    3. The file getting written to can't be enlarged.

Still that's some pretty decent landscape.

Finally:

        Initiate a pipe   
                |
                |
                |
               \ /
                V

       Fill it all with data  ======>  sets PIPE_BUF_FLAG_CAN_MERGE 
                |                            on all entries
                |
                |       |----> This only means reading until len = 0
               \ /      |   on all pipe buffer's entrances on the ring.
                V       |        (reads decrement the len index)
                        |             
          Drain the pipe     =======> this clears the contents on the 
                |                     pipe buffers while leaving their
                |                            flags unchanged.
                |
               \ /       |----> splice 1 byte just before the target's
                V        |               desired offset
          splice data from
           the target file  =======> assigns the page cache reference 
            to the pipe              to *page on the pipe_buffer as 
                |                    well as buf->offset and buf->len
                |
                |
               \ /
                V
            write data 
             into the   =======> Data will be appended to the file page
               pipe              on page cache due PIPE_BUF_FLAG_CAN_MERGE.
                                 Effectively writing on the page cache via
                                 the target's address.

An interesting fact is: The changes on the file does not necessarily persist, since
they are not applied to the file, they are just applied to a copy of the file's data, 
stored on the page cache (remember? the kernel copies the data from the disk to the 
page cache).

In our case, the page is never marked as dirty by the kernel. That happens because, the
changes made to the file were not made via the mechanism that would normally trigger a flip on the
dirty bit page on pages. The way this works is: 


# Conclusion and author's thought :D


So if you made it to here: Firstly, thank you for reading it!
I hope you understand a little bit more about Dirty Pipe after doing it.

I really enjoyed making this blogpost, as i said at the begginning i really enjoy
writing and i appreciatte A LOT when i read something that is well written
(clear structure, language, phrasing etc etc).

This was my first time "investigating" a vulnerability. I choose it because i've
always heard about the Dirty family of vulns but never really "saw" them, so i went
to read a little bit about them and selected Dirty Pipe!

As i was reading the discover (which is extremelly well written btw), i was kinda
shocked by the way the vuln was perceived. I strongly recommend to read it yourself,
not wanting to spoil it but the strange behaviour of the vuln was corrupting couple files
from Max's infrastructure.

Through the discovery, he narrates his process of investigation while explaining how
his log server worked. This is interesting because he didn't instantly betted that it would be
a kernel bug, he ruled out enough sources and deconstructed the working setup in order to
reach the root cause. I know this reads as a slooped generic phrase but the whole process
of changing the angle and reaching dead ends but trading it off for information on the bug

And in the end, he concluded it was a kernel bug by hacking two extremelly simple programs
(the ones mentioned on this post) that simulated the core behaviour of his log splitter and 
his web server! This is what made me like the disclosure so much. Is not the fact
that he found the vulnerability itself, but rather the way he did. The fact that he simulated
the "important" part of his enviroment behaviour in such a small but precise way which resulted
in confirming a kernel bug, for me, it's amazing.

But anyway people, thanks for reading it i hope i see you around :D



## References

- [Max Kellermann — The Dirty Pipe Vulnerability](https://dirtypipe.cm4all.com/)
- [Oracle Linux — An In-Depth Look at Pipe and Splice implementation in Linux kernel](https://blogs.oracle.com/linux/pipe-and-splice)
- [LWN.net — The iov_iter interface](https://lwn.net/Articles/625077/)
